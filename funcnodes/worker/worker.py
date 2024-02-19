from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import (
    List,
    Type,
    Callable,
    Tuple,
    Awaitable,
    TypedDict,
    Any,
    Literal,
    Optional,
    Dict,
    Union,
    get_type_hints,
)
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
from funcnodes import (
    NodeSpace,
    Shelf,
    FullNodeSpaceJSON,
    NodeSpaceJSON,
    Node,
    NodeJSON,
    JSONEncoder,
    JSONDecoder,
)
from funcnodes.lib import find_shelf
import traceback
from exposedfunctionality import exposed_method


class MetaInfo(TypedDict):
    id: str
    version: str


class NodeViewState(TypedDict):
    pos: Tuple[int, int]
    size: Tuple[int, int]


class ViewState(TypedDict):
    nodes: dict[str, NodeViewState]


class State(TypedDict):
    backend: NodeSpaceJSON
    view: ViewState
    meta: MetaInfo
    dependencies: dict[str, List[str]]


class FullState(TypedDict):
    backend: FullNodeSpaceJSON
    view: ViewState
    worker: dict[str, list[str]]


class MEvent(TypedDict):
    type: Literal["mevent"]
    event: str
    data: Any


class CmdMessage(TypedDict):
    type: Literal["cmd"]
    cmd: str
    kwargs: dict
    id: str | None


class ResultMessage(TypedDict):
    type: Literal["result"]
    id: str | None
    result: Any


class ErrorMessage(TypedDict):
    type: Literal["error"]
    error: str
    tb: List[str]
    id: str | None


class NodeUpdateJSON(NodeJSON):
    """
    NodeUpdateJSON is the interface for the serialization of a Node with additional data
    """

    frontend: NodeViewState


JSONMessage = Union[CmdMessage, ResultMessage, ErrorMessage]


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
        self._client.nodespace.lib.add_nodes(
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
        default_nodes: List[Shelf] | None = None,
        nodespace_delay=0.005,
        local_worker_lookup_delay=5,
        save_delay=5,
    ) -> None:
        if default_nodes is None:
            default_nodes = []

        self.logger = logging.getLogger(__name__)

        self.data_path = os.path.abspath(data_path)

        self.loop_manager = LoopManager(self)
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
        self.nodespace.on_error(self._on_nodespaceerror)

        for shelf in default_nodes:
            self.nodespace.lib.add_shelf(shelf)

        self._nodespace_id: str = uuid.uuid4().hex
        self.viewdata: ViewState = {"nodes": {}}

    # region properties
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

    @property
    def nodespace_id(self) -> str:
        return self._nodespace_id

    # endregion properties

    # region states
    @exposed_method()
    def view_state(self) -> ViewState:
        available_nodeids = []
        if "nodes" not in self.viewdata:
            self.viewdata["nodes"] = {}
        for node in self.nodespace.nodes:
            available_nodeids.append(node.uuid)
            if node.uuid not in self.viewdata["nodes"]:
                self.viewdata["nodes"][node.uuid] = NodeViewState(
                    pos=(0, 0),
                    size=(200, 250),
                )
        excess_nodes = set(self.viewdata["nodes"].keys()) - set(available_nodeids)
        for nodeid in excess_nodes:
            del self.viewdata["nodes"][nodeid]
        return self.viewdata

    @exposed_method()
    def get_meta(self) -> MetaInfo:
        return {
            "id": self.nodespace_id,
            "version": funcnodes.__version__,
        }

    @exposed_method()
    def get_state(self) -> State:
        data: State = {
            "backend": self.nodespace.serialize(),
            "view": self.view_state(),
            "meta": self.get_meta(),
            "dependencies": self.nodespace.lib.get_dependencies(),
        }
        return data

    @exposed_method()
    def full_state(self):
        data = {
            "backend": self.nodespace.full_serialize(),
            "view": self.view_state(),
            "worker": {
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
                for w in self.local_worker_lookup_loop.worker_classes
            },
            "meta": {
                "id": self.nodespace_id,
                "version": funcnodes.__version__,
            },
        }
        return data

    @exposed_method()
    def get_library(self) -> dict:
        return self.nodespace.lib.full_serialize()

    # endregion states

    # region save and load
    def request_save(self):
        self.saveloop.request_save()

    def save(self):
        data: State = self.get_state()
        with open(self.local_nodespace, "w+", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, cls=JSONEncoder))
        return data

    async def load(self, data: State | str | None = None):
        if data is None:
            if not os.path.exists(self.local_nodespace):
                return
            with open(self.local_nodespace, "r", encoding="utf-8") as f:
                data: State = json.loads(f.read(), cls=JSONDecoder)

        if isinstance(data, str):
            data: State = json.loads(data, cls=JSONDecoder)

        if "backend" not in data:
            data["backend"] = {}
        if "view" not in data:
            data["view"] = {}

        if "nodes" in data["backend"]:
            nodes = data["backend"]["nodes"]
            for node in nodes:
                await self.install_node(node)

        if "meta" in data:
            if "id" in data["meta"]:
                self._set_nodespace_id(data["meta"]["id"])
        self.nodespace.deserialize(data["backend"])
        self.viewdata = data["view"]

        return self.save()

    # endregion save and load

    # region events

    @abstractmethod
    def _on_nodespaceevent(self, event, **kwargs):
        """handle nodespace events"""

    @abstractmethod
    def _on_nodespaceerror(
        self,
        error: Exception,
        src: NodeSpace,
    ):
        """handle nodespace errors"""

    # endregion events

    # region nodespace interaction

    # region library

    @exposed_method()
    def add_shelf_by_module(self, module: str):
        shelf = find_shelf(module=module)
        if shelf is None:
            raise ValueError(f"Shelf with module {module} not found")
        self.nodespace.lib.add_dependency(module=module)
        self.nodespace.lib.add_shelf(shelf)
        return True

    # endregion library

    # region nodes

    @exposed_method()
    def add_node(self, id: str, **kwargs):
        return self.nodespace.add_node_by_id(id, **kwargs)

    @exposed_method()
    def get_node(self, id: str) -> Node:
        return self.nodespace.get_node_by_id(id)

    @exposed_method()
    def set_io_value(
        self,
        nid: str,
        ioid: str,
        value: Any,
        set_default: bool = False,
        trigger: bool = False,
    ):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        if set_default:
            io.set_default(value)
        io.set_value(value)
        print("set value", value, trigger)
        if trigger:
            node.request_trigger()
        return io.value

    @exposed_method()
    def get_io_value(self, nid: str, ioid: str):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        return io.value

    @exposed_method()
    def set_default_value(self, nid: str, ioid: str, value: Any):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        io.set_default(value)
        self.request_save()
        return True

    @exposed_method()
    def get_node_state(self, nid: str) -> NodeJSON:
        node = self.get_node(nid)
        return node._repr_json_()

    @exposed_method()
    def request_trigger(self, nid: str):
        node = self.get_node(nid)
        node.request_trigger()
        return True

    @exposed_method()
    def update_node(self, nid: str, data: NodeUpdateJSON):
        node = self.get_node(nid)

        if not node:
            raise ValueError(f"Node with id {nid} not found")
        ans = {}
        if "frontend" in data:
            ans["frontend"] = self.update_node_view(nid, data["frontend"])

        if "name" in data:
            n = data["name"]
            node.name = n
            ans["name"] = node.name
        self.request_save()
        return ans

    @exposed_method()
    def update_node_view(self, nid: str, data: NodeViewState):
        if nid not in self.viewdata["nodes"]:
            self.viewdata["nodes"][nid] = data
        else:
            self.viewdata["nodes"][nid].update(data)
        return self.viewdata["nodes"][nid]

    # endregion nodespace interaction

    async def install_node(self, nodedata: NodeJSON):
        nideid = nodedata["node_id"]
        if self.nodespace.lib.has_node_id(nideid):
            return
        await self.local_worker_lookup_loop.loop()

        for req in nodedata.get("requirements", []):
            if req["type"] == "nodeclass":
                _class = req["class"]
                _id = req["id"]
                for cls in self.local_worker_lookup_loop.worker_classes:
                    if cls.NODECLASSID == _class:
                        self.local_worker_lookup_loop.start_local_worker(cls, _id)

        if self.nodespace.lib.has_node_id(nideid):
            return

        raise ValueError(f"Node with id {nideid} not found")

    def _set_nodespace_id(self, nsid: str):
        if nsid is None:
            nsid = uuid.uuid4().hex

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

        self.logger.debug(f"check packages to install {packages}")
        missing = []
        for p in packages:
            try:
                importlib.import_module(p)
            except ImportError:
                missing.append(p)
        if len(missing) > 0:
            self.logger.info(f"check install {packages}")
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


async def get_all_nodeio_reps(
    nodespace: NodeSpace,
) -> Dict[str, NodeJSON]:
    data = {}
    for node in nodespace.nodes:
        if node.uuid not in data:
            data[node.uuid] = node._repr_json_()
    return data


class TriggerNode(TypedDict):
    id: str


class TriggerOutLoop(CustomLoop):
    def __init__(self, client: RemoteWorker, delay=0.2) -> None:
        super().__init__(delay=delay)
        self._last_states = {}
        self._client = client

    async def loop(self):
        new_states = {}
        for node in self._client.nodespace.nodes:
            new_states[node.uuid] = node.is_working

        changed_states = {
            node_id: new_state
            for node_id, new_state in new_states.items()
            if new_state != self._last_states.get(node_id, None)
        }
        self._last_states = new_states

        if len(changed_states) == 0:
            return

        new_triggers: List[TriggerNode] = [
            {"id": node_id}
            for node_id, new_state in changed_states.items()
            if new_state
        ]
        new_trigger_dones: List[TriggerNode] = [
            {"id": node_id}
            for node_id, new_state in changed_states.items()
            if not new_state
        ]

        if len(new_triggers) > 0:
            event_bundle: MEvent = {
                "type": "mevent",
                "event": "trigger",
                "data": new_triggers,
            }
            self._client.send(event_bundle)

        if len(new_trigger_dones) > 0:
            event_bundle: MEvent = {
                "type": "mevent",
                "event": "trigger_done",
                "data": new_trigger_dones,
            }
            await self._client.send(event_bundle)


class NodeSpaceEvent(TypedDict):
    type: Literal["nsevent"]
    event: str
    data: Dict[str, Any]


class RemoteWorker(Worker):
    def __init__(self, *args, trigger_delay=0.05, data_delay=0.2, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.trigger_out_loop = TriggerOutLoop(self, delay=trigger_delay)
        self.loop_manager.add_loop(self.trigger_out_loop)

        self._messagehandlers: List[
            Callable[[dict], Awaitable[Tuple[bool | None, str]]]
        ] = []
        self.add_messagehandler(self._handle_cmd_message)

    async def send(self, data, **kwargs):
        data = json.dumps(data, cls=JSONEncoder)
        await self.sendmessage(data, **kwargs)

    @abstractmethod
    async def sendmessage(self, msg: str, **kwargs):
        """send a message to the frontend"""

    def _on_nodespaceevent(self, event, src: NodeSpace, **kwargs):
        event_bundle: NodeSpaceEvent = {
            "type": "nsevent",
            "event": event,
            "data": kwargs,
        }
        self.send(event_bundle)
        return event_bundle

    def _on_nodespaceerror(
        self,
        error: Exception,
        src: NodeSpace,
    ):
        """handle nodespace errors"""
        error_bundle = {
            "type": "error_event",
            "error": repr(error),
            "tb": list(traceback.TracebackException.from_exception(error).format()),
        }
        self.send(error_bundle)

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

    def new_backend_instance(self, workerid):
        self.local_worker_lookup_loop.start_local_worker_by_id(workerid)

    async def sync_state(self) -> FullState:
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
        target: str,
        targetid: str,
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
