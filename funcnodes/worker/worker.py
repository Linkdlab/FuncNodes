from __future__ import annotations
from abc import ABC, abstractmethod
from logging.handlers import RotatingFileHandler
from functools import wraps
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
from uuid import uuid4
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
    NodeClassNotFoundError,
    NodeOutput,
    NodeInput,
)
from funcnodes.utils import deep_fill_dict
from funcnodes.lib import find_shelf
import traceback
from exposedfunctionality import exposed_method, get_exposed_methods
from typing_extensions import deprecated


class MetaInfo(TypedDict):
    id: str
    version: str


class NodeViewState(TypedDict):
    pos: Tuple[int, int]
    size: Tuple[int, int]


class ViewState(TypedDict):
    nodes: dict[str, NodeViewState]
    renderoptions: funcnodes.config.RenderOptions


class State(TypedDict):
    backend: NodeSpaceJSON
    view: ViewState
    meta: MetaInfo
    dependencies: dict[str, List[str]]


class ProgressState(TypedDict):
    message: str
    status: str
    progress: float
    blocking: bool


class FullState(TypedDict):
    backend: FullNodeSpaceJSON
    view: ViewState
    worker: dict[str, list[str]]
    progress_state: ProgressState
    meta: MetaInfo


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


class ProgressStateMessage(ProgressState, TypedDict):
    type: Literal["progress"]


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


JSONMessage = Union[CmdMessage, ResultMessage, ErrorMessage, ProgressStateMessage]


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

        for root, dirs, files in os.walk(self.path):  # pylint: disable=unused-variable
            for file in files:
                if file.endswith(".py") and file not in self._parsed_files:
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
                return self.start_local_worker(worker_class, uuid4().hex)

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
        self._client._write_process_file()
        self._client._write_config()
        if self.save_requested:
            self._client.save()
        self.save_requested = False


def requests_save(func):
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(self: Worker, *args, **kwargs):
            res = func(self, *args, **kwargs)
            self.request_save()
            return res

        return async_wrapper
    else:

        @wraps(func)
        def wrapper(self: Worker, *args, **kwargs):
            res = func(self, *args, **kwargs)
            self.request_save()
            return res

        return wrapper


class WorkerJson(TypedDict):
    type: str
    uuid: str
    data_path: str
    env_path: str
    shelves_dependencies: List[str]


class RemoteWorkerJson(WorkerJson):
    pass


class Worker(ABC):
    def __init__(
        self,
        data_path: str | None = None,
        default_nodes: List[Shelf] | None = None,
        nodespace_delay=0.005,
        local_worker_lookup_delay=5,
        save_delay=5,
        uuid: str | None = None,
    ) -> None:
        if default_nodes is None:
            default_nodes = []

        self._shelves_dependencies: List[str] = []
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

        self._nodespace_id: str = uuid4().hex
        self.viewdata: ViewState = {
            "nodes": {},
            "renderoptions": funcnodes.config.FUNCNODES_RENDER_OPTIONS,
        }
        self._uuid = uuid4().hex if not uuid else uuid
        self.data_path = (
            os.path.abspath(data_path)
            if data_path
            else os.path.join(
                funcnodes.config.CONFIG_DIR, "workers", "worker_" + self._uuid
            )
        )
        self.logger = funcnodes.get_logger(self._uuid, propagate=False)
        self.logger.addHandler(
            RotatingFileHandler(
                os.path.join(self.data_path, "worker.log"),
                maxBytes=100000,
                backupCount=5,
            )
        )

        self._exposed_methods = get_exposed_methods(self)
        self._progress_state: ProgressState = {
            "message": "",
            "status": "",
            "progress": 0,
            "blocking": False,
        }

    @property
    def _process_file(self):
        return os.path.join(
            funcnodes.config.CONFIG_DIR,
            "workers",
            "worker_" + self._uuid + ".p",
        )

    def _write_process_file(self):
        if not os.path.exists(self._process_file):
            with open(self._process_file, "w+") as f:
                pass
        else:
            with open(self._process_file, "r") as f:
                d = f.read()
            if d != "":
                try:
                    self.loop_manager.async_call(self.run_cmd(json.loads(d)))
                except Exception as e:
                    pass

    def _write_config(self) -> WorkerJson:
        c = self.generate_config()
        cfile = os.path.join(
            funcnodes.config.CONFIG_DIR,
            "workers",
            "worker_" + self._uuid + ".json",
        )
        if os.path.exists(cfile):
            with open(
                cfile,
                "r",
                encoding="utf-8",
            ) as f:
                oldc = json.load(f)

            c = deep_fill_dict(
                oldc, c, overwrite_existing=True, merge_lists=True, unfify_lists=True
            )
        with open(
            cfile,
            "w+",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(c, indent=2))

        return c

    def ini_config(self):
        if os.path.exists(self._process_file):
            raise RuntimeError("Worker already running")
        self._write_process_file()
        c = self._write_config()

        if "shelves_dependencies" in c:
            for dep in c["shelves_dependencies"]:
                try:
                    self.add_shelf(dep, save=False)
                except Exception as e:
                    self.logger.exception(e)

    def generate_config(self) -> WorkerJson:
        return {
            "uuid": self._uuid,
            "data_path": self.data_path,
            "type": self.__class__.__name__,
            "env_path": os.path.abspath(os.path.join(self.data_path, "env")),
            "shelves_dependencies": self._shelves_dependencies,
        }

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

    def add_local_worker(self, worker_class: Type[FuncNodesExternalWorker], nid: str):
        return self.local_worker_lookup_loop.start_local_worker(worker_class, nid)

    # region states
    @exposed_method()
    def uuid(self) -> str:
        return self._uuid

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

        self.viewdata["renderoptions"] = funcnodes.config.FUNCNODES_RENDER_OPTIONS
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
    def full_state(self) -> FullState:
        data = FullState(
            backend=self.nodespace.full_serialize(),
            view=self.view_state(),
            worker={
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
                for w in self.local_worker_lookup_loop.worker_classes
            },
            progress_state=self._progress_state,
            meta=self.get_meta(),
        )

        return data

    @exposed_method()
    def get_library(self) -> dict:
        return self.nodespace.lib.full_serialize()

    # endregion states

    # region save and load
    def request_save(self):
        self.saveloop.request_save()

    @exposed_method()
    def save(self):
        data: State = self.get_state()
        with open(self.local_nodespace, "w+", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, cls=JSONEncoder))
        self._write_config()
        return data

    @exposed_method()
    def load_data(self, data: State):
        return self.loop_manager.async_call(self.load(data))

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
                try:
                    await self.install_node(node)
                except NodeClassNotFoundError:
                    pass

        if "meta" in data:
            if "id" in data["meta"]:
                self._set_nodespace_id(data["meta"]["id"])
        self.nodespace.deserialize(data["backend"])
        self.viewdata = data["view"]

        return self.request_save()

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

    def add_shelves_dependency(self, src: str):
        if src not in self._shelves_dependencies:
            self._shelves_dependencies.append(src)

    async def set_progress_state(
        self, message: str, status: str, progress: float, blocking: bool
    ):
        self._progress_state = {
            "message": message,
            "status": status,
            "progress": progress,
            "blocking": blocking,
        }

    def set_progress_state_sync(self, *args, **kwargs):
        self.loop_manager.async_call(self.set_progress_state(*args, **kwargs))

    @exposed_method()
    def add_shelf(self, src: str, save=True):

        self.set_progress_state_sync(
            message="Adding shelf", status="info", progress=0.0, blocking=True
        )
        try:
            shelf = find_shelf(src=src)
            if shelf is None:
                raise ValueError(f"Shelf in {src} not found")
            self.add_shelves_dependency(src)
            self.nodespace.add_shelf(shelf)
            if save:
                self.request_save()
            self.set_progress_state_sync(
                message="Shelf added", status="success", progress=1, blocking=False
            )
        finally:
            pass
        return True

    @deprecated(
        "Use add_shelf instead",
    )
    def add_shelf_by_module(self, module: str):
        return self.add_shelf(module)

    # endregion library

    # region nodes
    @exposed_method()
    def clear(self):
        self.nodespace.clear()

    @requests_save
    @exposed_method()
    def add_node(self, id: str, **kwargs: Dict[str, Any]):
        return self.nodespace.add_node_by_id(id, **kwargs)

    @exposed_method()
    def get_node(self, id: str) -> Node:
        return self.nodespace.get_node_by_id(id)

    @requests_save
    @exposed_method()
    def remove_node(self, id: str) -> str:
        return self.nodespace.remove_node_by_id(id)

    @exposed_method()
    def set_io_value(self, nid: str, ioid: str, value: Any, set_default: bool = False):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        if set_default:
            io.set_default(value)
        io.set_value(value)

        return io.value

    @exposed_method()
    def get_io_value(self, nid: str, ioid: str):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        return io.value

    @exposed_method()
    def trigger_node(self, nid: str):
        node = self.get_node(nid)
        node.request_trigger()
        return True

    @requests_save
    @exposed_method()
    def set_default_value(self, nid: str, ioid: str, value: Any):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        io.set_default(value)
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

    @requests_save
    @exposed_method()
    def update_node(self, nid: str, data: NodeUpdateJSON):
        try:
            node = self.get_node(nid)
        except Exception:
            return {"error": f"Node with id {nid} not found"}
        if not node:
            raise ValueError(f"Node with id {nid} not found")
        ans = {}
        if "frontend" in data:
            ans["frontend"] = self.update_node_view(nid, data["frontend"])

        if "name" in data:
            n = data["name"]
            node.name = n
            ans["name"] = node.name

        return ans

    @requests_save
    @exposed_method()
    def update_node_view(self, nid: str, data: NodeViewState):
        if nid not in self.viewdata["nodes"]:
            self.viewdata["nodes"][nid] = data
        else:
            self.viewdata["nodes"][nid].update(data)
        return self.viewdata["nodes"][nid]

    @exposed_method()
    async def stop_worker(self):
        await self.set_progress_state(
            message="Stopping worker", status="info", progress=0.0, blocking=True
        )
        await asyncio.sleep(0.1)
        self.stop()
        await self.set_progress_state(
            message="Stopping worker", status="info", progress=1, blocking=False
        )
        return True

    # endregion nodes
    # region edges
    @requests_save
    @exposed_method()
    def add_edge(
        self,
        src_nid: str,
        src_ioid: str,
        trg_nid: str,
        trg_ioid: str,
        replace: bool = False,
    ):
        src = self.get_node(src_nid)
        tgt = self.get_node(trg_nid)
        srcio = src.get_input_or_output(src_ioid)
        tgtio = tgt.get_input_or_output(trg_ioid)
        if isinstance(srcio, NodeOutput) and isinstance(tgtio, NodeInput):
            return srcio.connect(tgtio, replace=replace)
        else:
            return tgtio.connect(srcio, replace=replace)

    @requests_save
    @exposed_method()
    def remove_edge(
        self,
        src_nid: str,
        src_ioid: str,
        trg_nid: str,
        trg_ioid: str,
    ):
        src = self.get_node(src_nid)
        tgt = self.get_node(trg_nid)
        srcio = src.get_input_or_output(src_ioid)
        tgtio = tgt.get_input_or_output(trg_ioid)

        srcio.disconnect(tgtio)
        return True

    # endregion edges
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

        raise NodeClassNotFoundError(f"Node with id {nideid} not found")

    def _set_nodespace_id(self, nsid: str):
        if nsid is None:
            nsid = uuid4().hex

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
        self.logger.info("Starting worker forever")
        self.ini_config()
        self.initialize_nodespace()
        try:
            self.loop_manager.run_forever()
        finally:
            self.stop()

    def stop(self):
        self.logger.info("Stopping worker")
        self.loop_manager.stop()
        os.remove(self._process_file)

    def __del__(self):
        self.stop()

    async def run_cmd(self, json_msg: CmdMessage):
        cmd = json_msg["cmd"]
        if cmd not in self._exposed_methods:
            raise Exception(
                f"Unknown command {cmd} , available commands: {', '.join(self._exposed_methods.keys())}"
            )
        kwargs = json_msg.get("kwargs", {})
        func = self._exposed_methods[cmd][0]
        if asyncio.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = func(**kwargs)
        return result


class TriggerNode(TypedDict):
    id: str


class NodeSpaceEvent(TypedDict):
    type: Literal["nsevent"]
    event: str
    data: Dict[str, Any]


class RemoteWorker(Worker):
    def __init__(self, *args, trigger_delay=0.05, data_delay=0.2, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._messagehandlers: List[
            Callable[[dict], Awaitable[Tuple[bool | None, str]]]
        ] = []

    async def set_progress_state(self, *args, **kwargs):
        await super().set_progress_state(*args, **kwargs)
        await self.send(ProgressStateMessage(type="progress", **self._progress_state))

    async def send(self, data, **kwargs):
        data = json.dumps(data, cls=JSONEncoder)
        await self.sendmessage(data, **kwargs)

    @abstractmethod
    async def sendmessage(self, msg: str, **kwargs):
        """send a message to the frontend"""

    def _on_nodespaceevent(self, event, src: NodeSpace, **kwargs):
        if event in {
            "before_set_value",
            "before_request_trigger",
            "after_request_trigger",
            "before_disconnect",
            "before_connect",
            "before_trigger",
            "after_trigger",
        }:
            return
        if event == "node_trigger_error":
            self.logger.exception(kwargs["error"])
        event_bundle: NodeSpaceEvent = {
            "type": "nsevent",
            "event": event,
            "data": kwargs,
        }

        self.loop_manager.async_call(self.send(event_bundle))
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
        self.logger.exception(error)
        self.loop_manager.async_call(self.send(error_bundle))

    async def recieve_message(self, json_msg: dict, **sendkwargs):
        if "type" not in json_msg:
            return
        try:
            if json_msg["type"] == "cmd":
                await self._handle_cmd_msg(json_msg, **sendkwargs)
        except Exception as e:
            await self.send(
                ErrorMessage(
                    type="error",
                    error=str(e),
                    tb=traceback.format_exception(e),
                    id=json_msg.get("id"),
                )
            )

    async def _handle_cmd_msg(self, json_msg: CmdMessage, **sendkwargs):
        result = await self.run_cmd(json_msg)
        await self.send(
            ResultMessage(type="result", result=result, id=json_msg.get("id")),
            **sendkwargs,
        )

    def generate_config(self) -> RemoteWorkerJson:
        return super().generate_config()
