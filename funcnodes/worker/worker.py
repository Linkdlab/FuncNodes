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
    NoValue,
)
from funcnodes_core.utils import saving
from funcnodes_core.lib import find_shelf, ShelfDict
from exposedfunctionality import exposed_method, get_exposed_methods
from typing_extensions import deprecated

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
    external_workers: Dict[str, List[str]]


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
        self._client.write_config()
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


class BaseWorkerDict(TypedDict):
    module: str
    worker_classes: List[ExternalWorkerSerClass]


class PackageWorkerDict(BaseWorkerDict):
    package: str
    version: str


class PathWorkerDict(BaseWorkerDict):
    path: str


WorkerDict = Union[BaseWorkerDict, PackageWorkerDict, PathWorkerDict]


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


def find_worker_from_path(
    path: Union[str, PathWorkerDict],
) -> Union[Tuple[List[Type[FuncNodesExternalWorker]], WorkerDict], None]:
    if isinstance(path, str):
        path = path.replace("\\", os.sep).replace("/", os.sep)
        path = path.strip(os.sep)

        data = PathWorkerDict(
            path=os.path.dirname(os.path.abspath(path)),
            module=os.path.basename(path),
            worker_classes=[],
        )
    else:
        data = path

    if not os.path.exists(data["path"]):
        raise FileNotFoundError(f"file {data['path']} not found")

    if data["path"] not in sys.path:
        sys.path.insert(0, data["path"])

    # install requirements
    if "pyproject.toml" in os.listdir(data["path"]):
        funcnodes.FUNCNODES_LOGGER.debug(
            f"pyproject.toml found in {data['path']}, generating requirements.txt"
        )
        # install poetry requirements
        # save current path
        cwd = os.getcwd()
        # cd into the module path
        os.chdir(data["path"])
        # install via poetry
        os.system("poetry update --no-interaction")
        os.system(
            "poetry export --without-hashes -f requirements.txt --output requirements.txt"
        )
        # cd back
        os.chdir(cwd)
    if "requirements.txt" in os.listdir(data["path"]):
        funcnodes.FUNCNODES_LOGGER.debug(
            f"requirements.txt found in {data['path']}, installing requirements"
        )
        # install pip requirements
        os.system(
            f"{sys.executable} -m pip install -r {os.path.join(data['path'],'requirements.txt')}"
        )

    ndata = find_worker_from_module(data)
    if ndata is not None:
        return ndata[0], PackageWorkerDict(**{**data, **ndata[1]})


def find_worker_from_module(
    mod: Union[str, BaseWorkerDict],
) -> Union[Tuple[List[Type[FuncNodesExternalWorker]], WorkerDict], None]:
    try:
        strmod: str
        if isinstance(mod, dict):
            dat = mod
            strmod = mod["module"]
        else:
            strmod = mod
            dat = BaseWorkerDict(module=strmod, worker_classes=[])

        # submodules = strmod.split(".")

        module = importlib.import_module(strmod)

        # for submod in submodules[1:]:
        #     mod = getattr(mod, submod)
        workercls = module_to_worker(module)
        dat["worker_classes"] = []
        for worker_class in workercls:
            dat["worker_classes"].append(
                {
                    "module": strmod,
                    "class_name": worker_class.__name__,
                    "name": getattr(worker_class, "NAME", worker_class.__name__),
                    "_classref": worker_class,
                }
            )

        return workercls, dat

    except (ModuleNotFoundError, KeyError) as e:
        funcnodes.FUNCNODES_LOGGER.exception(e)
        return None


def find_worker_from_package(
    pgk: Union[str, PackageWorkerDict],
) -> Union[Tuple[List[Type[FuncNodesExternalWorker]], WorkerDict], None]:
    if isinstance(pgk, str):
        # remove possible version specifier
        stripped_src = pgk.split("=", 1)[0]
        stripped_src = pgk.split(">", 1)[0]
        stripped_src = pgk.split("<", 1)[0]
        stripped_src = pgk.split("~", 1)[0]
        stripped_src = pgk.split("!", 1)[0]
        stripped_src = pgk.split("@", 1)[0]
        data = {}
        data["package"] = stripped_src
        if "/" in pgk:
            data["module"] = pgk.rsplit("/", 1)[-1]
            basesrc = pgk.rsplit("/", 1)[0]
        else:
            data["module"] = data["package"]
            basesrc = pgk
        data["version"] = basesrc.replace(data["package"], "")

        data = PackageWorkerDict(
            package=data["package"],
            module=data["module"],
            version=data["version"],
            worker_classes=[],
        )
        try:
            os.system(
                f"{sys.executable} -m pip install {data['package']}{data['version']} --upgrade -q"
            )
        except Exception as e:
            funcnodes.FUNCNODES_LOGGER.exception(e)
            return None
    else:
        data = pgk

    ndata = find_worker_from_module(data)
    if ndata is not None:
        return ndata[0], PackageWorkerDict(**{**data, **ndata[1]})


def find_worker(
    src: Union[WorkerDict, str],
) -> Tuple[List[Type[FuncNodesExternalWorker]], WorkerDict] | None:
    if isinstance(src, dict):
        if "path" in src:
            dat = find_worker_from_path(src)

            if dat is not None:
                return dat

        if "package" in src:
            dat = find_worker_from_package(src)
            if dat is not None:
                return dat

        if "module" in src:
            dat = find_worker_from_module(src)

            if dat is not None:
                return dat

        return None

    # check if identifier is a python module e.g. "funcnodes.lib"
    funcnodes.FUNCNODES_LOGGER.debug(f"trying to import {src}")

    if src.startswith("pip://"):
        src = src[6:]
        return find_worker_from_package(src)

    # check if file path:
    if src.startswith("file://"):
        # unifiy path between windows and linux
        src = src[7:]
        return find_worker_from_path(src)

    # try to get via pip
    return find_worker_from_module(src)


class WorkerJson(TypedDict):
    type: str
    uuid: str
    name: str | None
    data_path: str
    env_path: str
    python_path: str

    shelves_dependencies: List[ShelfDict]
    worker_dependencies: List[WorkerDict]


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
    ) -> None:
        if default_nodes is None:
            default_nodes = []

        self._shelves_dependencies: List[ShelfDict] = []
        self._worker_dependencies: List[WorkerDict] = []
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
        self.nodespace.on_error(self._on_nodespaceerror)

        for shelf in default_nodes:
            self.nodespace.lib.add_shelf(shelf)

        self._nodespace_id: str = uuid4().hex
        self.viewdata: ViewState = {
            "nodes": {},
            "renderoptions": funcnodes.config.FUNCNODES_RENDER_OPTIONS,
        }
        self._uuid = uuid4().hex if not uuid else uuid
        self._name = name
        self._data_path: str = (
            os.path.abspath(data_path)
            if data_path
            else os.path.join(
                funcnodes.config.CONFIG_DIR, "workers", "worker_" + self._uuid
            )
        )
        self.data_path = self._data_path
        funcnodes.logging.set_logging_dir(self.data_path)
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
                except Exception:
                    pass

    @property
    def config(self) -> WorkerJson | None:
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
            return oldc
        return None

    def write_config(self, opt_conf: Optional[WorkerJson] = None) -> WorkerJson:
        if opt_conf is None:
            c = self.generate_config()
        else:
            c = opt_conf
        c["uuid"] = self._uuid
        cfile = os.path.join(
            funcnodes.config.CONFIG_DIR,
            "workers",
            "worker_" + self._uuid + ".json",
        )
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
        c = self.write_config()

        if "worker_dependencies" in c:
            for dep in list(c["worker_dependencies"]):
                try:
                    self.add_worker_package(dep, save=False)
                except Exception as e:
                    self.logger.exception(e)

        if "shelves_dependencies" in c:
            for dep in c["shelves_dependencies"]:
                try:
                    self.add_shelf(dep, save=False)
                except Exception as e:
                    self.logger.exception(e)

    def generate_config(self) -> WorkerJson:
        oldc = self.config
        if oldc is None:
            oldc = {}
        uuid = self._uuid
        name = oldc.get("name") or self._name
        data_path = self.data_path
        env_path = os.path.abspath(os.path.join(self.data_path, "env"))
        sds: List[ShelfDict] = []  # not using set to assure order

        for sd in oldc.get("shelves_dependencies", []):
            if sd not in sds:
                sds.append(sd)
        for sd in self._shelves_dependencies:
            if sd not in sds:
                sds.append(sd)

        worker_dependencies: List[WorkerDict] = []

        def w_in_without_classes(w: WorkerDict):
            cs = w.copy()
            cs["worker_classes"] = []
            csj = json.dumps(cs, sort_keys=True, cls=JSONEncoder)
            for w2 in worker_dependencies:
                w2 = w2.copy()
                w2["worker_classes"] = []
                if csj == json.dumps(w2, sort_keys=True, cls=JSONEncoder):
                    return True
            return False

        for w in self._worker_dependencies:
            if not w_in_without_classes(w):
                worker_dependencies.append(w)
        for w in oldc.get("worker_dependencies", []):
            if not w_in_without_classes(w):
                worker_dependencies.append(w)
        python_path = sys.executable
        return WorkerJson(
            type=self.__class__.__name__,
            uuid=uuid,
            name=name,
            data_path=data_path,
            env_path=env_path,
            shelves_dependencies=sds,
            python_path=python_path,
            worker_dependencies=worker_dependencies,
        )

    # region properties
    @property
    def data_path(self) -> str:
        return self._data_path

    @data_path.setter
    def data_path(self, data_path: str):
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

    @exposed_method()
    def add_external_worker(self, module: str, cls_module: str, cls_name: str):
        for wdep in self._worker_dependencies:
            if wdep["module"] == module:
                for wcls in wdep["worker_classes"]:
                    if wcls["class_name"] == cls_name and wcls["module"] == cls_module:
                        return self.add_local_worker(wcls["_classref"], uuid4().hex)
        raise ValueError(f"Worker {cls_name}({cls_module}) not found in {module}")

    @exposed_method()
    def get_worker_dependencies(self) -> List[WorkerDict]:
        return self._worker_dependencies

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
                w.NODECLASSID: [i.uuid for i in w.running_instances()]
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
    def get_library(self) -> dict:
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
        data: WorkerState = self.get_save_state()
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
                    worker_id, worker_uuid, self.local_worker_lookup_loop.worker_classes
                )
                for worker in self.local_worker_lookup_loop.worker_classes:
                    if worker.NODECLASSID == worker_id:
                        for instance in worker_uuid:
                            self.add_local_worker(worker, instance)

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

    def add_shelves_dependency(self, src: str | ShelfDict):
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
    def add_shelf(self, src: Union[str, ShelfDict], save: bool = True):
        self.set_progress_state_sync(
            message="Adding shelf", status="info", progress=0.0, blocking=True
        )
        try:
            shelfdata = find_shelf(src=src)
            if shelfdata is None:
                return {"error": f"Shelf in {src} not found"}
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

    def add_worker_dependency(self, src: WorkerDict):
        if src not in self._worker_dependencies:
            self._worker_dependencies.append(src)
            for worker_class in src["worker_classes"]:
                if (
                    worker_class["_classref"]
                    not in self.local_worker_lookup_loop.worker_classes
                ):
                    self.local_worker_lookup_loop.worker_classes.append(
                        worker_class["_classref"]
                    )

    @exposed_method()
    def add_worker_package(self, src: Union[str, WorkerDict], save=True):
        self.set_progress_state_sync(
            message="Adding worker", status="info", progress=0.0, blocking=True
        )
        try:
            worker_data = find_worker(src=src)
            if worker_data is None:
                return {"error": f"Worker in {src} not found"}
            worker, worker_data = worker_data

            if worker is None:
                raise ValueError(f"Worker in {src} not found")
            self.add_worker_dependency(worker_data)

            if save:
                self.request_save()
            self.set_progress_state_sync(
                message="Worker added", status="success", progress=1, blocking=False
            )
        finally:
            pass
        return True

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
    def set_io_value(self, nid: str, ioid: str, value: Any, set_default: bool = False):
        node = self.get_node(nid)
        io = node.get_input(ioid)
        if (
            set_default and value != NoValue
        ):  # novalue should not be set automatically as default via io set
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
        self.logger.info("Stopping")
        self.loop_manager.stop()
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
