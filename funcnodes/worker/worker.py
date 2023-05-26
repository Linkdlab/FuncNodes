from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import List, Type, Callable, Tuple, Awaitable
import os
import json
import asyncio
import sys
import importlib
import importlib.util
import inspect
import uuid
import funcnodes
from funcnodes.worker.loop import LoopManager, NodeSpaceLoop, CustomLoop
from funcnodes.worker.external_worker import FuncNodesExternalWorker
from funcnodes.nodespace import NodeSpace, LibShelf
from funcnodes.node import Node
import numpy as np
import traceback


class LocalWorkerLookupLoop(CustomLoop):
    class WorkerNotFoundError(Exception):
        pass

    def __init__(self, client: Worker, path=None, delay=5) -> None:
        super().__init__(delay)

        self._path = path
        self._client: Worker = client
        self.worker_classes: List[Type[FuncNodesExternalWorker]] = []
        self._parsed_files = []

    @property
    def path(self):
        if self._path is None:
            p = self._client.local_scripts
        else:
            p = self._path

        if not os.path.exists(p):
            os.mkdir(p)

        if p not in sys.path:
            sys.path.insert(0, p)

        return p

    @path.setter
    def path(self, path):
        self._path = path

    async def loop(self):
        # get all .py files in path (deep)

        print("looking for workers", self.worker_classes)
        for root, dirs, files in os.walk(self.path):  # pylint: disable=unused-variable
            for file in files:
                if file.endswith(".py") and file not in self._parsed_files:
                    print(os.path.join(root, file))
                    module_name = file[:-3]
                    spec = importlib.util.spec_from_file_location(
                        module_name, os.path.join(root, file)
                    )
                    if spec is None:
                        continue
                    if spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for (
                        name,  # pylint: disable=unused-variable
                        obj,
                    ) in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, FuncNodesExternalWorker)
                            and obj != FuncNodesExternalWorker
                        ):
                            if obj not in self.worker_classes:
                                self.worker_classes.append(obj)

                    self._parsed_files.append(file)

        # import gc
        # import objgraph

        # gc.collect()
        # for k, v in FuncNodesExternalWorker.RUNNING_WORKERS.items():
        #    for id, n in v.items():
        #        print("#" * 10)
        #                print(k, id, n)
        #                print(gc.get_referrers(n), len(gc.get_referrers(n)))
        #        objgraph.show_backrefs([n], filename=f"{n}.png", max_depth=5,too_many=)

        # print("-" * 10)
        # TODO: memory leak somewhere, the instance is never removed

    def start_local_worker(
        self, worker_class: Type[FuncNodesExternalWorker], worker_id: str
    ):
        if worker_class not in self.worker_classes:
            self.worker_classes.append(worker_class)
        worker_instance: FuncNodesExternalWorker = worker_class(workerid=worker_id)
        self._client.loop_manager.add_loop(worker_instance)
        self._client.nodespace.lib.add_nodeclasses(
            worker_instance.get_all_nodeclasses(), ["local", worker_instance.uuid]
        )

        return worker_instance

    def start_local_worker_by_id(self, worker_id: str):
        for worker_class in self.worker_classes:
            if worker_class.NODECLASSID == worker_id:
                return self.start_local_worker(worker_class, uuid.uuid4().hex)

        raise LocalWorkerLookupLoop.WorkerNotFoundError(
            "No worker with id " + worker_id
        )

    def stop_local_worker_by_id(self, worker_id: str, instance_id: str):
        if worker_id in FuncNodesExternalWorker.RUNNING_WORKERS:
            if instance_id in FuncNodesExternalWorker.RUNNING_WORKERS[worker_id]:
                worker_instance = FuncNodesExternalWorker.RUNNING_WORKERS[worker_id][
                    instance_id
                ]
                self._client.nodespace.lib.remove_nodeclasses(
                    worker_instance.get_all_nodeclasses()
                )
                worker_instance.stop()
                self._client.loop_manager.remove_loop(worker_instance)
                return True
            else:
                raise LocalWorkerLookupLoop.WorkerNotFoundError(
                    "No worker with instance id " + instance_id
                )

        raise LocalWorkerLookupLoop.WorkerNotFoundError(
            "No worker with id " + worker_id + " and instance id " + instance_id
        )


class SaveLoop(CustomLoop):
    def __init__(self, client: Worker, delay=5) -> None:
        super().__init__(delay)
        self._client: Worker = client
        self.save_requested = False

    def request_save(self):
        self.save_requested = True

    async def loop(self):
        if self.save_requested:
            self._client.save()
        self.save_requested = False


class Worker(ABC):
    def __init__(
        self,
        data_path: str,
        default_nodes: List[LibShelf] | None = None,
        nodespace_delay=0.005,
        local_worker_lookup_delay=5,
        save_delay=5,
    ) -> None:
        if default_nodes is None:
            default_nodes = []

        self.data_path = os.path.abspath(data_path)

        self.loop_manager = LoopManager()
        self.nodespace = NodeSpace()

        self.nodespace_loop = NodeSpaceLoop(self.nodespace, delay=nodespace_delay)
        self.loop_manager.add_loop(self.nodespace_loop)

        self.local_worker_lookup_loop = LocalWorkerLookupLoop(
            client=self,
            delay=local_worker_lookup_delay,
        )
        self.loop_manager.add_loop(self.local_worker_lookup_loop)

        self.saveloop = SaveLoop(self, delay=save_delay)
        self.loop_manager.add_loop(self.saveloop)

        self.nodespace.on("*", self._on_nodespaceevent)

        for shelf in default_nodes:
            self.nodespace.lib.add_shelf(shelf)

        self._nodespace_id: str | None = None
        self.viewdata = {}

    @property
    def data_path(self):
        return self._data_path

    @data_path.setter
    def data_path(self, data_path):
        data_path = os.path.abspath(data_path)
        if not os.path.exists(data_path):
            os.mkdir(data_path)
        self._data_path = data_path

    @property
    def local_nodespace(self):
        return os.path.join(self.data_path, "nodespace.json")

    @property
    def local_scripts(self):
        return os.path.join(self.data_path, "local_scripts")

    def view_state(self):
        available_nodeids = []
        if "nodes" not in self.viewdata:
            self.viewdata["nodes"] = {}
        for node in self.nodespace.nodes:
            available_nodeids.append(node.id)
            if node.id not in self.viewdata["nodes"]:
                self.viewdata["nodes"][node.id] = {}
            if "pos" not in self.viewdata["nodes"][node.id]:
                self.viewdata["nodes"][node.id]["pos"] = [0, 0]
            if "size" not in self.viewdata["nodes"][node.id]:
                self.viewdata["nodes"][node.id]["size"] = [200, 250]

        excess_nodes = set(self.viewdata["nodes"].keys()) - set(available_nodeids)
        for nodeid in excess_nodes:
            del self.viewdata["nodes"][nodeid]
        return self.viewdata

    def get_state(self):
        data = {
            "backend": self.nodespace.serialize(),
            "view": self.view_state(),
            "meta": {
                "id": self.nodespace_id,
                "version": funcnodes.__version__,
            },
        }
        return data

    def request_save(self):
        self.saveloop.request_save()

    def save(self):
        data = self.get_state()
        with open(self.local_nodespace, "w+", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2))
        return data

    @abstractmethod
    def _on_nodespaceevent(self, event, **kwargs):
        """handle nodespace events"""

    def full_state(self):
        data = {
            "backend": self.nodespace.full_serialize(),
            "view": self.view_state(),
            "worker": {
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
                for w in self.local_worker_lookup_loop.worker_classes
            },
        }
        return data

    async def load(self, data=None):
        if data is None:
            if not os.path.exists(self.local_nodespace):
                return
            with open(self.local_nodespace, "r", encoding="utf-8") as f:
                data = json.loads(f.read())

        if isinstance(data, str):
            data = json.loads(data)

        if "backend" not in data:
            data["backend"] = {}
        if "view" not in data:
            data["view"] = {}

        if "nodes" in data["backend"]:
            nodes = data["backend"]["nodes"]
            for node in nodes:
                for req in node.get("requirements", []):
                    if req["type"] == "nodeclass":
                        if self.nodespace.lib.has_node_id(node["nid"]):
                            continue
                        _class = req["class"]
                        _id = req["id"]
                        await self.local_worker_lookup_loop.loop()
                        for cls in self.local_worker_lookup_loop.worker_classes:
                            if cls.NODECLASSID == _class:
                                self.local_worker_lookup_loop.start_local_worker(
                                    cls, _id
                                )
                                break

        if "meta" in data:
            if "id" in data["meta"]:
                self.nodespace_id = data["meta"]["id"]
        self.nodespace.deserialize(data["backend"])
        self.viewdata = data["view"]

        return self.save()

    @property
    def nodespace_id(self) -> str | None:
        return self._nodespace_id

    @nodespace_id.setter
    def nodespace_id(self, nsid: str):
        if nsid is None:
            self._nodespace_id = None
            return

        if len(nsid) == 32:
            self._nodespace_id = nsid
        else:
            raise ValueError("nsid must be 32 characters long")

    def initialize_nodespace(self):
        try:
            self.loop_manager._loop.run_until_complete(self.load())
        except FileNotFoundError:
            pass

    def run_forever(self):
        self.initialize_nodespace()
        self.loop_manager.run_forever()


async def get_all_nodeio_reps(
    nodespace: NodeSpace,
):
    data = {}
    for node in nodespace.nodes:
        if node.id not in data:
            data[node.id] = node._repr_json_()
    return data


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "_repr_json_"):
            return obj._repr_json_()
        if isinstance(obj, np.ndarray):
            return obj.tolist()

        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class DataUpdateLoop(CustomLoop):
    def __init__(self, client: RemoteWorker, delay=1.0) -> None:
        super().__init__(delay)
        self._client = client
        self._active_data = {}

    def reset_active_data(self):
        self._active_data = {}

    async def loop(self):
        changed_data = {}
        all_data = await get_all_nodeio_reps(self._client.nodespace)
        for nodeid in list(self._active_data.keys()):
            if nodeid not in all_data:
                del self._active_data[nodeid]

        for nodeid, node_repr in all_data.items():
            if nodeid not in self._active_data:
                self._active_data[nodeid] = {}
            for ioid, ioval in node_repr["io"].items():
                if ioid not in self._active_data[nodeid]:
                    self._active_data[nodeid][ioid] = {
                        "value": "null",
                        "mime": "text/plain",
                    }
                if (
                    self._active_data[nodeid][ioid]["value"] != ioval["value"]["value"]
                    or self._active_data[nodeid][ioid]["mime"] != ioval["value"]["mime"]
                ):
                    self._active_data[nodeid][ioid]["value"] = ioval["value"]["value"]
                    self._active_data[nodeid][ioid]["mime"] = ioval["value"]["mime"]
                    if nodeid not in changed_data:
                        changed_data[nodeid] = {}
                    changed_data[nodeid][ioid] = self._active_data[nodeid][ioid]

        if len(changed_data) > 0:
            event_bundle = {
                "type": "mevent",
                "event": "value_update",
                "data": changed_data,
            }
            self._client.send(event_bundle)


class TriggerOutLoop(CustomLoop):
    def __init__(self, client: RemoteWorker, delay=0.2) -> None:
        super().__init__(delay=delay)
        self._last_states = {}
        self._client = client

    async def loop(self):
        new_states = {}
        for node in self._client.nodespace.nodes:
            new_states[node.id] = node.is_working

        changed_states = {
            node_id: new_state
            for node_id, new_state in new_states.items()
            if new_state != self._last_states.get(node_id, None)
        }
        self._last_states = new_states

        if len(changed_states) == 0:
            return

        new_triggers = [
            {"id": node_id}
            for node_id, new_state in changed_states.items()
            if new_state
        ]
        new_trigger_dones = [
            {"id": node_id}
            for node_id, new_state in changed_states.items()
            if not new_state
        ]

        if len(new_triggers) > 0:
            event_bundle = {
                "type": "mevent",
                "event": "trigger",
                "data": new_triggers,
            }
            self._client.send(event_bundle)

        if len(new_trigger_dones) > 0:
            event_bundle = {
                "type": "mevent",
                "event": "trigger_done",
                "data": new_trigger_dones,
            }
            self._client.send(event_bundle)


class RemoteWorker(Worker):
    def __init__(self, *args, trigger_delay=0.05, data_delay=0.2, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.trigger_out_loop = TriggerOutLoop(self, delay=trigger_delay)
        self.loop_manager.add_loop(self.trigger_out_loop)

        self.data_update_loop = DataUpdateLoop(self, delay=data_delay)
        self.loop_manager.add_loop(self.data_update_loop)
        self.logger = logging.getLogger(__name__)

        self._messagehandlers: List[
            Callable[[dict], Awaitable[Tuple[bool | None, str]]]
        ] = []
        self.add_messagehandler(self._handle_cmd_message)

    def send(self, data):
        data = json.dumps(data, cls=JSONEncoder)
        self.sendmessage(data)

    @abstractmethod
    def sendmessage(self, msg: str):
        """send a message to the frontend"""

    def _on_nodespaceevent(self, event, **kwargs):
        event_bundle = {
            "type": "nsevent",
            "event": event,
            "data": kwargs,
        }
        self.send(event_bundle)

    async def targeted_command(self, data):
        target = data["target"]
        if target == "Node":
            node = self.nodespace.get_node(data["targetid"])
            if hasattr(node, data["cmd"]):
                res = getattr(node, data["cmd"])(
                    *data.get("args", []), **data.get("kwargs", {})
                )
                if asyncio.iscoroutine(res):
                    res = await res
                return True, res
            else:
                return False, "Invalid command"
        elif target == "NodeSpace":
            if hasattr(self.nodespace, data["cmd"]):
                res = getattr(self.nodespace, data["cmd"])(
                    *data.get("args", []), **data.get("kwargs", {})
                )
                if asyncio.iscoroutine(res):
                    res = await res
                return True, res
            else:
                return False, "Invalid command"
        elif target == "NodeIO":
            node = self.nodespace.get_node(data["targetid"].split("__")[0])
            io = node.get_input_or_output(data["targetid"].split("__")[1])
            if hasattr(io, data["cmd"]):
                res = getattr(io, data["cmd"])(
                    *data.get("args", []), **data.get("kwargs", {})
                )
                if asyncio.iscoroutine(res):
                    res = await res
                return True, res
            else:
                return False, "Invalid command"
        else:
            return False, "Invalid target"

    async def _handle_cmd_message(self, data):
        if "cmd" not in data:
            return None, "No cmd specified"
        handled = False
        undandled_message = "Unhandled cmd message"
        try:
            res = None
            if "target" in data and data["target"] is not None:
                ran, res = await self.targeted_command(data)
                if ran:
                    handled = True
                else:
                    undandled_message = res
            elif hasattr(self, data["cmd"]):
                try:
                    res = getattr(self, data["cmd"])(
                        *data.get("args", []), **data.get("kwargs", {})
                    )
                    if asyncio.iscoroutine(res):
                        res = await res
                    handled = True
                except Exception as exc:
                    self.logger.exception(exc)
                    undandled_message = repr(exc)

            if handled:
                data["result"] = res
                data["type"] = "worker_result"

                self.send(data)

        except Exception as exc:
            self.logger.exception(exc)
            undandled_message = repr(exc)
            data["result"] = None
            data["error"] = undandled_message
            data["type"] = "error_event"
            data["tb"] = list(traceback.TracebackException.from_exception(exc).format())
            self.send(data)

        return handled, undandled_message

    def full_state(self):
        data = {
            "backend": self.nodespace.full_serialize(),
            "view": self.view_state(),
            "worker": {
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
                for w in self.local_worker_lookup_loop.worker_classes
            },
        }
        return data

    def new_backend_instance(self, workerid):
        self.local_worker_lookup_loop.start_local_worker_by_id(workerid)

    async def sync_state(self):
        data = self.full_state()
        self.data_update_loop.reset_active_data()
        return data

    async def set_view_attribute(
        self,
        attr,
        value,
        target,
        targetid,
    ):
        if target == "Node":
            if targetid not in self.viewdata["nodes"]:
                self.viewdata["nodes"][targetid] = {}
            self.viewdata["nodes"][targetid][attr] = value

    async def update_view_data(
        self,
        data,
        target,
        targetid,
    ):
        if target == "Node":
            if targetid not in self.viewdata["nodes"]:
                self.viewdata["nodes"][targetid] = {}
            self.viewdata["nodes"][targetid].update(data)

    def add_messagehandler(
        self, handler: Callable[[dict], Awaitable[Tuple[bool | None, str]]]
    ) -> None:
        self._messagehandlers.append(handler)

    async def recieve(self, data: dict):
        handled = False
        undandled_message = "Unhandled message"
        for messagehandler in self._messagehandlers:
            handled, _undandled_message = await messagehandler(data)
            if handled:
                break
            if handled is None:
                continue
            undandled_message = _undandled_message

        if not handled:
            self.logger.error("%s: %s", undandled_message, json.dumps(data))

    async def install_package(self, package: str):
        import importlib

        try:
            importlib.import_module(package)
        except ImportError:
            import subprocess
            import sys

            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "my_package"]
            )

    async def install_packages(self, packages: List[str]):
        import importlib

        missing = []
        for p in packages:
            try:
                importlib.import_module(p)
            except ImportError:
                missing.append(p)
        if len(missing) > 0:
            import subprocess
            import sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

    async def add_remote_node(self, data: dict, libpath: List[str] | None = None):
        fielstring = """from funcnodes import Node, NodeInput, NodeOutput
"""
        for mod, implist in data.get("imports", {}).items():
            line = ""
            if mod != "":
                line += f"from {mod} import "
            else:
                line += "import "
            line += (
                ", ".join(
                    [
                        imp["name"]
                        + (" as " + imp["asname"] if "asname" in imp else "")
                        for imp in implist
                    ]
                )
                + "\n"
            )
            if line.startswith("from __future__ "):
                fielstring = line + fielstring
            else:
                fielstring += line

        fielstring += "\n" * 2
        fielstring += (
            data["content"]
            .replace("{name}", data["name"])
            .replace("{nid}", data["nid"])
        )

        if libpath is None:
            libpath = ["custom"]

        target_path = os.path.join(self.data_path, "nodes")
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        target_path = os.path.join(target_path, data["nid"] + ".py")
        with open(target_path, "w+") as f:
            f.write(fielstring)

        await self.install_packages(data.get("dependencies", []))

        try:
            basename = os.path.basename(target_path)
            module_name = basename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, target_path)
            if spec is None:
                return
            if spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for (
                name,  # pylint: disable=unused-variable
                obj,
            ) in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Node)
                    and obj.__name__ == data["name"]
                ):
                    nodeclass = obj
                    self.nodespace.lib.add_nodeclass(nodeclass, libpath)

        except Exception as e:
            self.logger.exception(e)

        self.nodespace.emit("node_library_updated")
