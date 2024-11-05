from __future__ import annotations
from abc import ABC, abstractmethod
from logging.handlers import RotatingFileHandler
from functools import wraps
from typing import (
    List,
    Type,
    Tuple,
    TypedDict,
    Any,
    Literal,
    Optional,
    Dict,
    Union,
)
import os
import time
import json
import asyncio
import sys
import importlib
import importlib.util
import inspect
from uuid import uuid4
import funcnodes
from funcnodes.worker.loop import LoopManager, NodeSpaceLoop, CustomLoop
from funcnodes.worker.external_worker import (
    FuncNodesExternalWorker,
    FuncNodesExternalWorkerJson,
)
from funcnodes import (
    NodeSpace,
    Shelf,
    NodeSpaceJSON,
    Node,
    NodeJSON,
    JSONEncoder,
    JSONDecoder,
    NodeClassNotFoundError,
    FullLibJSON,
)
from funcnodes_core.utils import saving
from funcnodes_core.lib import find_shelf, ShelfDict
from exposedfunctionality import exposed_method, get_exposed_methods
from typing_extensions import deprecated
import subprocess_monitor
import threading
from weakref import WeakSet
from ..utils import AVAILABLE_REPOS, reload_base, install_repo, try_import_module

try:
    from funcnodes_react_flow import (
        FUNCNODES_REACT_PLUGIN,
        get_react_plugin_content,
    )

    FUNCNODES_REACT = True
except (ModuleNotFoundError, ImportError):
    FUNCNODES_REACT = False

from funcnodes_core.nodespace import FullNodeJSON


class MetaInfo(TypedDict):
    id: str
    version: str


class NodeViewState(TypedDict):
    pos: Tuple[int, int]
    size: Tuple[int, int]


class ViewState(TypedDict):
    nodes: dict[str, NodeViewState]
    renderoptions: funcnodes.config.RenderOptions


class WorkerState(TypedDict):
    backend: NodeSpaceJSON
    view: ViewState
    meta: MetaInfo
    dependencies: dict[str, List[str]]
    external_workers: Dict[str, List[FuncNodesExternalWorkerJson]]


class ProgressState(TypedDict):
    message: str
    status: str
    progress: float
    blocking: bool


class FullState(TypedDict):
    backend: NodeSpace
    view: ViewState
    worker: dict[str, list[str]]
    progress_state: ProgressState
    meta: MetaInfo
    worker_dependencies: List[WorkerDict]


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

EXTERNALWORKERLIB = "_external_worker"


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
        tasks = []
        # for id, instancedict in FuncNodesExternalWorker.RUNNING_WORKERS.items():
        #     for instance in instancedict.values():
        #         if instance.stopped:
        #             tasks.append(self.stop_local_worker_by_id(id, instance.uuid))
        # print(instance.name, "references:", gc.get_referrers(instance))

        await asyncio.gather(*tasks)

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

    def _worker_instance_stopping_callback(
        self, src: FuncNodesExternalWorker, **kwargs
    ):
        try:
            asyncio.get_event_loop().create_task(
                self.stop_local_worker_by_id(src.NODECLASSID, src.uuid)
            )
        except Exception as e:
            print(e)

    def start_local_worker(
        self, worker_class: Type[FuncNodesExternalWorker], worker_id: str
    ):
        if worker_class not in self.worker_classes:
            self.worker_classes.append(worker_class)
        worker_instance: FuncNodesExternalWorker = worker_class(workerid=worker_id)

        worker_instance.on(
            "stopping",
            self._worker_instance_stopping_callback,
        )
        self._client.loop_manager.add_loop(worker_instance)

        self._client.nodespace.lib.add_nodes(
            worker_instance.get_all_nodeclasses(),
            [EXTERNALWORKERLIB, worker_instance.uuid],
        )

        self._client.request_save()

        return worker_instance

    def start_local_worker_by_id(self, worker_id: str):
        for worker_class in self.worker_classes:
            if worker_class.NODECLASSID == worker_id:
                return self.start_local_worker(worker_class, uuid4().hex)

        raise LocalWorkerLookupLoop.WorkerNotFoundError(
            "No worker with id " + worker_id
        )

    async def stop_local_worker_by_id(self, worker_id: str, instance_id: str):
        if worker_id in FuncNodesExternalWorker.RUNNING_WORKERS:
            if instance_id in FuncNodesExternalWorker.RUNNING_WORKERS[worker_id]:
                worker_instance = FuncNodesExternalWorker.RUNNING_WORKERS[worker_id][
                    instance_id
                ]
                self._client.nodespace.lib.remove_nodeclasses(
                    worker_instance.get_all_nodeclasses()
                )

                self._client.nodespace.lib.remove_shelf_path(
                    [EXTERNALWORKERLIB, worker_instance.uuid]
                )

                timeout_duration = 5
                self._client.logger.info(
                    f"Stopping worker {worker_id} instance {instance_id}"
                )
                try:
                    await asyncio.wait_for(
                        worker_instance.stop(), timeout=timeout_duration
                    )
                except asyncio.TimeoutError:
                    self._client.logger.warning(
                        "Timeout: worker_instance.stop() did not complete within "
                        f"{timeout_duration} seconds for worker {worker_id} instance {instance_id}"
                    )

                self._client.logger.info(
                    f"Stopped worker {worker_id} instance {instance_id}"
                )

                self._client.loop_manager.remove_loop(worker_instance)
                del worker_instance

                await self._client.worker_event("external_worker_update")
                self._client.request_save()
                return True
            else:
                raise LocalWorkerLookupLoop.WorkerNotFoundError(
                    "No worker with instance id " + instance_id
                )

        raise LocalWorkerLookupLoop.WorkerNotFoundError(
            "No worker with id " + worker_id + " and instance id " + instance_id
        )

    async def stop_local_workers_by_id(self, worker_id: str) -> bool:
        if worker_id in FuncNodesExternalWorker.RUNNING_WORKERS:
            tasks = []
            for instance_id in list(
                FuncNodesExternalWorker.RUNNING_WORKERS[worker_id].keys()
            ):
                tasks.append(self.stop_local_worker_by_id(worker_id, instance_id))

            # Run all tasks in parallel
            await asyncio.gather(*tasks)
            #
            return True
        return False


class SaveLoop(CustomLoop):
    def __init__(self, client: Worker, delay=5) -> None:
        super().__init__(delay)
        self._client: Worker = client
        self.save_requested = False

    def request_save(self):
        self.save_requested = True

    async def loop(self):
        self._client._write_process_file()
        # self._client.write_config()
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


class HeartbeatLoop(CustomLoop):
    def __init__(self, client: Worker, required_heatbeat=None, delay=5) -> None:
        if required_heatbeat is not None:
            required_heatbeat = float(required_heatbeat)
            delay = min(delay, required_heatbeat / 10)

        super().__init__(delay)
        self._client: Worker = client
        self.required_heatbeat = required_heatbeat
        self._last_heartbeat = time.time()

    def heartbeat(self):
        self._last_heartbeat = time.time()

    async def loop(self):
        if self.required_heatbeat is not None:
            if time.time() - self._last_heartbeat > self.required_heatbeat:
                asyncio.create_task(self._client.stop_worker())


class ExternalWorkerSerClass(TypedDict):
    module: str
    class_name: str
    name: str
    _classref: Type[FuncNodesExternalWorker]
    instances: WeakSet[FuncNodesExternalWorker]


class WorkerDict(TypedDict):
    module: str
    worker_classes: List[ExternalWorkerSerClass]


class BasePackageDependency(TypedDict):
    package: str


class PipPackageDependency(BasePackageDependency):
    version: Optional[str]


class LocalPackageDependency(BasePackageDependency):
    path: str


PackageDependency = Union[PipPackageDependency, LocalPackageDependency]


def module_to_worker(mod) -> List[Type[FuncNodesExternalWorker]]:
    """
    Parses a single module for FuncNodesExternalWorker.
    """  #

    funcnodes.FUNCNODES_LOGGER.debug(f"parsing module {mod}")
    classes: List[Type[FuncNodesExternalWorker]] = []
    for sn in ["FUNCNODES_WORKER_CLASSES"]:  # typo in the original code
        if hasattr(mod, sn):
            worker_classes = getattr(mod, sn)
            if isinstance(worker_classes, (list, tuple)):
                for worker_class in worker_classes:
                    if issubclass(worker_class, FuncNodesExternalWorker):
                        classes.append(worker_class)
            elif issubclass(worker_classes, FuncNodesExternalWorker):
                classes.append(worker_classes)

            else:
                raise ValueError(
                    f"FUNCNODES_WORKER_CLASSES in {mod} "
                    "is not a list of FuncNodesExternalWorker classes "
                    "or a FuncNodesExternalWorker class"
                )

    return classes


class WorkerJson(TypedDict):
    type: str
    uuid: str
    name: str | None
    data_path: str
    env_path: str
    python_path: str
    pid: Optional[int]

    # shelves_dependencies: Dict[str, ShelfDict]
    worker_dependencies: Dict[str, WorkerDict]
    package_dependencies: Dict[str, PackageDependency]


class Worker(ABC):
    def __init__(
        self,
        data_path: str | None = None,
        default_nodes: List[Shelf] | None = None,
        nodespace_delay=0.005,
        local_worker_lookup_delay=5,
        save_delay=5,
        required_heatbeat=None,
        uuid: str | None = None,
        name: str | None = None,
        debug: bool = False,
        **kwargs,  # catch all additional arguments for future compatibility
    ) -> None:
        if default_nodes is None:
            default_nodes = []

        self._debug = debug
        self._package_dependencies: Dict[str, PackageDependency] = {}
        # self._shelves_dependencies: Dict[str, ShelfDict] = {}
        self._worker_dependencies: Dict[str, WorkerDict] = {}
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

        self.heartbeatloop = HeartbeatLoop(self, required_heatbeat=required_heatbeat)
        self.loop_manager.add_loop(self.heartbeatloop)

        self.nodespace.on("*", self._on_nodespaceevent)
        self.nodespace.lib.on("*", self._on_libevent)
        self.nodespace.on_error(self._on_nodespaceerror)

        for shelf in default_nodes:
            self.nodespace.lib.add_shelf(shelf)

        self._nodespace_id: str = uuid4().hex
        self.viewdata: ViewState = {
            "nodes": {},
            "renderoptions": funcnodes.config.FUNCNODES_RENDER_OPTIONS,
        }
        self._uuid = uuid4().hex if not uuid else uuid
        self._name = name or None
        self._data_path: str = (
            os.path.abspath(data_path)
            if data_path
            else os.path.join(
                funcnodes.config.CONFIG_DIR, "workers", "worker_" + self.uuid()
            )
        )
        self.data_path = self._data_path
        funcnodes.logging.set_logging_dir(self.data_path)
        self.logger = funcnodes.get_logger(self.uuid(), propagate=False)
        if debug:
            self.logger.setLevel("DEBUG")
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
        self._save_disabled = False

    @property
    def _process_file(self):
        return os.path.join(
            funcnodes.config.CONFIG_DIR,
            "workers",
            "worker_" + self.uuid() + ".p",
        )

    @property
    def _config_file(self):
        return os.path.join(
            funcnodes.config.CONFIG_DIR,
            "workers",
            "worker_" + self.uuid() + ".json",
        )

    def _write_process_file(self):
        pf = self._process_file
        if not os.path.exists(os.path.dirname(pf)):
            os.makedirs(os.path.dirname(pf), exist_ok=True)
        if os.path.exists(pf):
            with open(pf, "r") as f:
                d = f.read()
            if d != "":
                try:
                    cmd = json.loads(d)
                    if not isinstance(
                        cmd, int
                    ):  # highly probable that data is an int (pid)
                        self.loop_manager.async_call(self.run_cmd(cmd))
                except Exception:
                    pass
        with open(pf, "w+") as f:
            f.write(str(os.getpid()))

    # region config

    @property
    def config(self) -> WorkerJson:
        return self.load_or_generate_config()

    def load_config(self) -> WorkerJson | None:
        cfile = self._config_file
        oldc = None
        if os.path.exists(cfile):
            with open(
                cfile,
                "r",
                encoding="utf-8",
            ) as f:
                oldc = json.load(f)
        if oldc:
            if "name" in oldc:
                self._name = oldc["name"]
        return oldc

    def load_or_generate_config(self) -> WorkerJson:
        c = self.load_config()
        if c is None:
            c = self.generate_config()
        return c

    def generate_config(self) -> WorkerJson:
        uuid = self.uuid()
        name = self.name()
        data_path = self.data_path
        env_path = os.path.abspath(os.path.join(self.data_path, "env"))

        worker_dependencies: List[WorkerDict] = []
        python_path = sys.executable
        return self.update_config(
            WorkerJson(
                type=self.__class__.__name__,
                uuid=uuid,
                name=name,
                data_path=data_path,
                env_path=env_path,
                # shelves_dependencies=self._shelves_dependencies.copy(),
                python_path=python_path,
                worker_dependencies=worker_dependencies,
                package_dependencies=self._package_dependencies.copy(),
                pid=os.getpid(),
            )
        )

    def update_config(self, conf: WorkerJson) -> WorkerJson:
        conf["uuid"] = self.uuid()
        conf["name"] = self.name()
        conf["data_path"] = self.data_path
        conf["python_path"] = sys.executable
        conf["pid"] = os.getpid()

        # conf["shelves_dependencies"] = self._shelves_dependencies.copy()
        conf["package_dependencies"] = self._package_dependencies.copy()

        worker_dependencies = conf.get("worker_dependencies", {})
        if isinstance(worker_dependencies, list):
            worker_dependencies = {w["module"]: w for w in worker_dependencies}

        def w_in_without_classes(w: WorkerDict):
            cs = w.copy()
            cs["worker_classes"] = []
            csj = json.dumps(cs, sort_keys=True, cls=JSONEncoder)
            for k, w2 in worker_dependencies.items():
                w2 = w2.copy()
                w2["worker_classes"] = []
                if csj == json.dumps(w2, sort_keys=True, cls=JSONEncoder):
                    return True
            return False

        for k, v in self._worker_dependencies.items():
            if not w_in_without_classes(v):
                worker_dependencies[k] = v
        conf["worker_dependencies"] = worker_dependencies

        return conf

    def write_config(self, opt_conf: Optional[WorkerJson] = None) -> WorkerJson:
        if opt_conf is None:
            c = self.update_config(self.config)
        else:
            c = opt_conf
        c["uuid"] = self.uuid()
        c["pid"] = os.getpid()
        cfile = self._config_file
        if not os.path.exists(os.path.dirname(cfile)):
            os.makedirs(os.path.dirname(cfile), exist_ok=True)
        with open(
            cfile,
            "w+",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(c, indent=2, cls=JSONEncoder))

        return c

    def ini_config(self):
        if os.path.exists(self._process_file):
            raise RuntimeError("Worker already running")
        self._write_process_file()
        c = self.load_or_generate_config()

        if "package_dependencies" in c:
            for name, dep in c["package_dependencies"].items():
                try:
                    self.add_package_dependency(name, dep, save=False)
                except Exception as e:
                    self.logger.exception(e)

        # if "worker_dependencies" in c:
        #     for dep in list(c["worker_dependencies"]):
        #         try:
        #             self.add_worker_package(dep, save=False)
        #         except Exception as e:
        #             self.logger.exception(e)

        # TODO: remove in future version
        def _shelves_dependencies_to_package(shelfdep: ShelfDict) -> PackageDependency:
            d = BasePackageDependency(
                package=(
                    shelfdep["package"]
                    if "package" in shelfdep
                    else shelfdep["module"].replace("_", "-")
                )
            )

            if "version" in shelfdep:
                d = PipPackageDependency(
                    package=d["package"], version=shelfdep["version"]
                )

            if "path" in shelfdep:
                d = LocalPackageDependency(package=d["package"], path=shelfdep["path"])
            else:
                d = PipPackageDependency(
                    package=d["package"], version=shelfdep.get("version")
                )

            return d

        if "shelves_dependencies" in c:
            if isinstance(c["shelves_dependencies"], dict):
                for k, v in c["shelves_dependencies"].items():
                    try:
                        pkg = _shelves_dependencies_to_package(v)
                        self.add_package_dependency(pkg["package"], pkg, save=False)
                    except Exception as e:
                        self.logger.exception(e)
            elif isinstance(c["shelves_dependencies"], list):
                for dep in c["shelves_dependencies"]:
                    try:
                        pkg = _shelves_dependencies_to_package(dep)
                        self.add_package_dependency(pkg["package"], pkg, save=False)
                    except Exception as e:
                        self.logger.exception(e)

    # endregion config
    # region properties
    @property
    def data_path(self) -> str:
        return self._data_path

    @data_path.setter
    def data_path(self, data_path: str):
        data_path = os.path.abspath(data_path)
        if not os.path.exists(data_path):
            os.makedirs(data_path)
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

    # region local worker
    def add_local_worker(self, worker_class: Type[FuncNodesExternalWorker], nid: str):
        w = self.local_worker_lookup_loop.start_local_worker(worker_class, nid)
        self.loop_manager.async_call(self.worker_event("external_worker_update"))
        return w

    @exposed_method()
    def add_external_worker(self, module: str, cls_module: str, cls_name: str):
        if module in self._worker_dependencies:
            wdep = self._worker_dependencies[module]
            for wcls in wdep["worker_classes"]:
                if wcls["class_name"] == cls_name and wcls["module"] == cls_module:
                    return self.add_local_worker(wcls["_classref"], uuid4().hex)

        raise ValueError(f"Worker {cls_name}({cls_module}) not found in {module}")

    @exposed_method()
    def get_worker_dependencies(self) -> List[WorkerDict]:
        for k, v in self._worker_dependencies.items():
            for cls in v["worker_classes"]:
                cls["instances"] = WeakSet(cls["_classref"].running_instances())

        return list(self._worker_dependencies.values())

    @exposed_method()
    def update_external_worker(
        self,
        worker_id: str,
        class_id: str,
        name: Optional[str] = None,
    ):
        worker_instance = FuncNodesExternalWorker.RUNNING_WORKERS.get(class_id, {}).get(
            worker_id
        )
        if worker_instance is None:
            raise ValueError(f"Worker {worker_id} not found")
        if name is not None:
            worker_instance.name = name

        self.loop_manager.async_call(self.worker_event("external_worker_update"))

    @exposed_method()
    async def remove_external_worker(self, worker_id: str, class_id: str):
        res = await self.local_worker_lookup_loop.stop_local_worker_by_id(
            class_id, worker_id
        )

        return res

    # endregion local worker
    # region states
    @exposed_method()
    def uuid(self) -> str:
        return self._uuid

    @exposed_method()
    def name(self) -> str:
        return self._name

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
    def heartbeat(self):
        self.heartbeatloop.heartbeat()

    @exposed_method()
    def get_meta(self) -> MetaInfo:
        return {
            "id": self.nodespace_id,
            "version": funcnodes.__version__,
        }

    @exposed_method()
    def get_save_state(self) -> WorkerState:
        data: WorkerState = {
            "backend": saving.serialize_nodespace_for_saving(self.nodespace),
            "view": self.view_state(),
            "meta": self.get_meta(),
            "dependencies": self.nodespace.lib.get_dependencies(),
            "external_workers": {
                w.NODECLASSID: w.running_instances()
                for w in self.local_worker_lookup_loop.worker_classes
            },
        }
        return data

    @exposed_method()
    def full_state(self) -> FullState:
        data = FullState(
            backend=self.nodespace,
            view=self.view_state(),
            worker={
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
                for w in self.local_worker_lookup_loop.worker_classes
            },
            worker_dependencies=self.get_worker_dependencies(),
            progress_state=self._progress_state,
            meta=self.get_meta(),
        )

        return data

    @exposed_method()
    def get_library(self) -> FullLibJSON:
        return self.nodespace.lib.full_serialize()

    @exposed_method()
    def get_nodes(self, with_frontend: bool = False) -> List[FullNodeJSON]:
        nodes = self.nodespace.full_nodes_serialize()
        if with_frontend:
            nodes_viewdata = self.viewdata.get("nodes", {})
            for node in nodes:
                node["frontend"] = nodes_viewdata.get(
                    node["id"],
                    NodeViewState(
                        pos=(0, 0),
                        size=(200, 250),
                    ),
                )

        return nodes

    @exposed_method()
    def get_edges(self) -> List[Tuple[str, str, str, str]]:
        return self.nodespace.serialize_edges()

    @exposed_method()
    async def stop_worker(self):
        self.logger.info("Stopping worker")
        await self.set_progress_state(
            message="Stopping worker", status="info", progress=0.0, blocking=False
        )

        self.stop()
        await self.set_progress_state(
            message="Stopping worker", status="info", progress=1, blocking=False
        )
        return True

    @exposed_method()
    def get_plugin_keys(self, type: Literal["react"]) -> List[str]:
        if type == "react":
            return list(FUNCNODES_REACT_PLUGIN.keys())

        raise ValueError(f"Plugin type {type} not found")

    @exposed_method()
    def get_plugin(self, key: str, type: Literal["react"]) -> Any:
        if type == "react":
            return get_react_plugin_content(key)

        raise ValueError(f"Plugin type {type} not found")

    # endregion states

    # region save and load
    def request_save(self):
        self.saveloop.request_save()

    @exposed_method()
    def save(self):
        if self._save_disabled:
            return
        data: WorkerState = self.get_save_state()
        print("saving", data)
        with open(self.local_nodespace, "w+", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, cls=JSONEncoder))
        self.write_config()
        return data

    @exposed_method()
    def load_data(self, data: WorkerState):
        return self.loop_manager.async_call(self.load(data))

    async def load(self, data: WorkerState | str | None = None):
        if data is None:
            if not os.path.exists(self.local_nodespace):
                return
            with open(self.local_nodespace, "r", encoding="utf-8") as f:
                data: WorkerState = json.loads(f.read(), cls=JSONDecoder)

        if isinstance(data, str):
            data: WorkerState = json.loads(data, cls=JSONDecoder)

        if "backend" not in data:
            data["backend"] = {}
        if "view" not in data:
            data["view"] = {}

        if "external_workers" in data:
            for worker_id, worker_uuid in data["external_workers"].items():
                print(
                    "external_worker",
                    worker_id,
                    worker_uuid,
                    self.local_worker_lookup_loop.worker_classes,
                )
                found = False
                for worker in self.local_worker_lookup_loop.worker_classes:
                    if worker.NODECLASSID == worker_id:
                        for instance in worker_uuid:
                            if isinstance(instance, str):
                                w = self.add_local_worker(worker, instance)
                            else:
                                w = self.add_local_worker(worker, instance["uuid"])
                                if "name" in instance:
                                    w.name = instance["name"]
                            found = True
                            print("WORKER", w)
                if not found:
                    self.logger.warning(f"External worker {worker_id} not found")

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

    async def worker_event(self, event: str, **kwargs):
        await self.send(
            {
                "type": "workerevent",
                "event": event,
                "data": kwargs,
            }
        )

    async def send(self, data, **kwargs):
        """send data to the any reciever, in base class it is a no-op"""
        pass

    @abstractmethod
    def _on_nodespaceevent(self, event, **kwargs):
        """handle nodespace events"""

    def _on_libevent(self, event, **kwargs):
        """handle lib events"""
        self.loop_manager.async_call(self.worker_event("lib_update"))

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

    # def add_shelves_dependency(self, src: ShelfDict):
    #     self._shelves_dependencies[src["module"]] = src

    # def remove_shelves_dependency(self, src: ShelfDict):
    #     if src["module"] in self._shelves_dependencies:
    #         del self._shelves_dependencies[src["module"]]

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
    def add_shelf(self, src: Union[str, ShelfDict], save: bool = True):
        self.set_progress_state_sync(
            message="Adding shelf", status="info", progress=0.0, blocking=True
        )
        self.logger.info(f"Adding shelf {src}")
        try:
            shelfdata = find_shelf(src=src)
            if shelfdata is None:
                raise ValueError(f"Shelf in {src} not found")
            shelf, shelfdata = shelfdata
            if shelf is None:
                raise ValueError(f"Shelf in {src} not found")
            self.add_shelves_dependency(shelfdata)
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

    @exposed_method()
    def add_package_dependency(
        self, name: str, dep: Optional[PackageDependency] = None, save: bool = True
    ):
        if dep and "path" in dep:
            raise NotImplementedError("Local package dependencies not implemented")

        if name not in AVAILABLE_REPOS:
            try_import_module(name)
        if name not in AVAILABLE_REPOS:
            raise ValueError(
                f"Package {name} not found, available: {list(AVAILABLE_REPOS.keys())}"
            )

        repo = AVAILABLE_REPOS[name]
        if dep is None:
            dep = PipPackageDependency(
                package=repo.package_name,
                version=None,
            )
        if not repo:
            raise ValueError(f"Package {name} not found")

        if not repo.installed:
            repo = install_repo(name, version=dep.get("version", None))

        module = repo.moduledata

        if module is None:
            raise ValueError(f"Package {name} not found")

        shelf = module.entry_points.get("shelf")
        if shelf:
            self.nodespace.add_shelf(shelf)

        external_worker = module.entry_points.get("external_worker")

        if external_worker:
            if not isinstance(external_worker, (list, tuple)):
                external_worker = [external_worker]

            self.add_worker_dependency(
                WorkerDict(
                    module=repo.moduledata.name,
                    worker_classes=[
                        ExternalWorkerSerClass(
                            module=worker_class.__module__,
                            class_name=worker_class.__name__,
                            name=getattr(worker_class, "NAME", worker_class.__name__),
                            _classref=worker_class,
                            instances=WeakSet(worker_class.running_instances()),
                        )
                        for worker_class in external_worker
                        if issubclass(worker_class, FuncNodesExternalWorker)
                    ],
                )
            )
        self._package_dependencies[name] = PipPackageDependency(
            package=repo.package_name,
            version=dep.get("version", None),
        )

        if save:
            self.request_save()

    @exposed_method()
    async def remove_package_dependency(
        self, name: str, dep: Optional[PackageDependency] = None, save: bool = True
    ):
        if dep and "path" in dep:
            raise NotImplementedError("Local package dependencies not implemented")

        if name not in AVAILABLE_REPOS:
            raise ValueError(f"Package {name} not found")

        repo = AVAILABLE_REPOS[name]
        if dep is None:
            dep = PipPackageDependency(
                package=repo.package_name,
                version=None,
            )
        if not repo:
            raise ValueError(f"Package {name} not found")

        module = repo.moduledata

        if module is None:
            raise ValueError(f"Package {name} not found")

        shelf = module.entry_points.get("shelf")
        if shelf:
            self.nodespace.remove_shelf(shelf)

        external_worker = module.entry_points.get("external_worker")

        if external_worker:
            if not isinstance(external_worker, (list, tuple)):
                external_worker = [external_worker]

            await self.remove_worker_dependency(
                WorkerDict(
                    module=repo.moduledata.name,
                    worker_classes=[
                        ExternalWorkerSerClass(
                            module=worker_class.__module__,
                            class_name=worker_class.__name__,
                            name=getattr(worker_class, "NAME", worker_class.__name__),
                            _classref=worker_class,
                            instances=WeakSet(worker_class.running_instances()),
                        )
                        for worker_class in external_worker
                        if issubclass(worker_class, FuncNodesExternalWorker)
                    ],
                )
            )

        if name in self._package_dependencies:
            del self._package_dependencies[name]

        if save:
            self.request_save()

    @exposed_method()
    def remove_shelf(self, src: Union[str, ShelfDict], save: bool = True):
        shelfdata = find_shelf(src=src)
        if shelfdata is None:
            return {"error": f"Shelf in {src} not found"}
        shelf, shelfdata = shelfdata
        if shelf is None:
            raise ValueError(f"Shelf in {src} not found")

        self.remove_shelves_dependency(shelfdata)
        self.nodespace.remove_shelf(shelf)
        if save:
            self.request_save()

    def add_worker_dependency(self, src: WorkerDict):
        if src["module"] not in self._worker_dependencies:
            self._worker_dependencies[src["module"]] = src
            for worker_class in src["worker_classes"]:
                if (
                    worker_class["_classref"]
                    not in self.local_worker_lookup_loop.worker_classes
                ):
                    self.local_worker_lookup_loop.worker_classes.append(
                        worker_class["_classref"]
                    )

            self.loop_manager.async_call(
                self.worker_event(
                    event="update_worker_dependencies",
                    worker_dependencies=self.get_worker_dependencies(),
                )
            )

    async def remove_worker_dependency(self, src: WorkerDict):
        if src["module"] in self._worker_dependencies:
            del self._worker_dependencies[src["module"]]
            for worker_class in src["worker_classes"]:
                await self.local_worker_lookup_loop.stop_local_workers_by_id(
                    worker_class["_classref"].NODECLASSID
                )
                if (
                    worker_class["_classref"]
                    in self.local_worker_lookup_loop.worker_classes
                ):
                    self.local_worker_lookup_loop.worker_classes.remove(
                        worker_class["_classref"]
                    )

            self.loop_manager.async_call(
                self.worker_event(
                    event="update_worker_dependencies",
                    worker_dependencies=self.get_worker_dependencies(),
                )
            )
            self.loop_manager.async_call(self.worker_event("lib_update"))

    # @worexposed_method()
    # def add_worker_package(self, src: Union[str, WorkerDict], save=True):
    #     self.set_progress_state_sync(
    #         message="Adding worker", status="info", progress=0.0, blocking=True
    #     )
    #     try:
    #         worker_data = find_worker(src=src)
    #         if worker_data is None:
    #             return {"error": f"Worker in {src} not found"}
    #         worker, worker_data = worker_data

    #         if worker is None:
    #             raise ValueError(f"Worker in {src} not found")
    #         self.add_worker_dependency(worker_data)

    #         if save:
    #             self.request_save()
    #         self.set_progress_state_sync(
    #             message="Worker added", status="success", progress=1, blocking=False
    #         )
    #     finally:
    #         pass
    #     return True

    @exposed_method()
    def get_available_modules(self):
        reload_base()
        ans = {
            "installed": [],
            "active": [],
            "available": [],
        }
        for modname, moddata in AVAILABLE_REPOS.items():
            data = {
                "name": modname,
                "description": moddata.description or "No description available",
                "version": moddata.version or "latest",
                "homepage": moddata.homepage or "",
                "source": moddata.source or "",
            }
            if (
                # self._shelves_dependencies.get(modname.replace("-", "_")) is not None or
                self._worker_dependencies.get(modname.replace("-", "_")) is not None
                or self._package_dependencies.get(modname) is not None
            ):  # replace - with _ to avoid issues with module names
                ans["active"].append(data)
            else:
                if moddata.installed:
                    ans["installed"].append(data)
                else:
                    ans["available"].append(data)

        return ans

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
    def remove_node(self, id: str) -> Union[str, None]:
        return self.nodespace.remove_node_by_id(id)

    @exposed_method()
    def trigger_node(self, nid: str):
        node = self.get_node(nid)
        node.request_trigger()
        return True

    @exposed_method()
    def get_node_status(self, nid: str):
        node = self.get_node(nid)
        return node.status()

    @requests_save
    @exposed_method()
    def set_default_value(self, nid: str, ioid: str, value: Any):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        io.set_default(value)
        return True

    @exposed_method()
    def get_node_state(self, nid: str) -> FullNodeJSON:
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
    def update_io_options(
        self,
        nid: str,
        ioid: str,
        name: Optional[str] = None,
        hidden: Optional[bool] = None,
    ):
        node = self.get_node(nid)
        io = node.get_input_or_output(ioid)

        if name is not None:
            if len(name) == 0:
                name = io.uuid
            io.name = name

        if hidden is not None:
            if len(io.connections) > 0:
                hidden = False
            io.hidden = hidden
        return io

    @requests_save
    @exposed_method()
    def update_node_view(self, nid: str, data: NodeViewState):
        if nid not in self.viewdata["nodes"]:
            self.viewdata["nodes"][nid] = data
        else:
            self.viewdata["nodes"][nid].update(data)
        return self.viewdata["nodes"][nid]

    @exposed_method()
    def set_io_value(self, nid: str, ioid: str, value: Any, set_default: bool = False):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        if set_default:  # novalue should not be set automatically as default via io set
            io.set_default(value)
        io.set_value(value)
        return io.value

    @exposed_method()
    def get_io_value(self, nid: str, ioid: str):
        node = self.get_node(nid)
        io = node.get_input_or_output(ioid)
        return JSONEncoder.apply_custom_encoding(io.value, preview=True)

    @exposed_method()
    def get_ios_values(self, nid: str) -> Dict[str, Any]:
        node = self.get_node(nid)
        return {
            **{
                ioid: JSONEncoder.apply_custom_encoding(io.value, preview=True)
                for ioid, io in node.inputs.items()
            },
            **{
                ioid: JSONEncoder.apply_custom_encoding(io.value, preview=True)
                for ioid, io in node.outputs.items()
            },
        }

    @exposed_method()
    def get_io_full_value(self, nid: str, ioid: str):
        node = self.get_node(nid)
        io = node.get_input_or_output(ioid)
        return JSONEncoder.apply_custom_encoding(io.value, preview=False)

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
        return srcio.connect(tgtio, replace=replace)

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

    def _set_nodespace_id(self, nsid: str):
        if nsid is None:
            nsid = uuid4().hex

        if len(nsid) == 32:
            self._nodespace_id = nsid
        else:
            raise ValueError("nsid must be 32 characters long")

    def initialize_nodespace(self):
        try:
            self.loop_manager.async_call(self.load())
        except FileNotFoundError:
            pass

    def _prerun(self):
        reload_base(with_repos=False)
        self._save_disabled = True
        self.logger.info("Starting worker forever")
        self.loop_manager.reset_loop()
        self.ini_config()
        self.initialize_nodespace()
        self._save_disabled = False

        if os.environ.get("SUBPROCESS_MONITOR_PORT", None) is not None:
            if not os.environ.get("SUBPROCESS_MONITOR_KEEP_RUNNING"):
                subprocess_monitor.call_on_manager_death(
                    self.stop,
                )

    def run_forever(self):
        self._prerun()
        try:
            self.loop_manager.run_forever()
        finally:
            self.stop()

    async def run_forever_async(self):
        self._prerun()
        try:
            await self.loop_manager.run_forever_async()
        finally:
            self.stop()

    def run_forever_threaded(self):
        runthread = threading.Thread(target=self.run_forever, daemon=True)
        runthread.start()
        return runthread

    def stop(self):
        self.save()
        self._save_disabled = True

        self.logger.info("Stopping")
        self.loop_manager.stop()
        for handler in self.logger.handlers:
            handler.flush()
            handler.close()

        if os.path.exists(self._process_file):
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
