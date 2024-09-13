import os
from funcnodes_core import (
    NodeInput,
    NodeOutput,
    NodeIO,
    NodeConnectionError,
    MultipleConnectionsError,
    SameNodeConnectionError,
    NodeInputSerialization,
    NodeOutputSerialization,
    Node,
    get_nodeclass,
    run_until_complete,
    NodeSpace,
    FullNodeSpaceJSON,
    NodeSpaceJSON,
    FullLibJSON,
    Shelf,
    NodeJSON,
    NodeClassMixin,
    NodeDecorator,
    Library,
    find_shelf,
    JSONEncoder,
    JSONDecoder,
    NodeClassNotFoundError,
    FUNCNODES_LOGGER,
    get_logger,
    instance_nodefunction,
    config,
    RenderOptions,
    NoValue,
    DataEnum,
    add_type,
    types,
    NodeIOSerialization,
    lib,
    nodemaker,
    _logging as logging,
    Encdata,
    decorator,
    setup,
    NodeTriggerError,
)

from .worker import (
    FuncNodesExternalWorker,
    RemoteWorker,
    WSWorker,
    WorkerManager,
    assert_worker_manager_running,
)

if not os.environ.get("FUNCNODES_SKIP_SETUP"):
    setup()

__all__ = [
    "FuncNodesExternalWorker",
    "RemoteWorker",
    "WSWorker",
    "WorkerManager",
    "assert_worker_manager_running",
    "NodeInput",
    "NodeOutput",
    "NodeIO",
    "NodeConnectionError",
    "MultipleConnectionsError",
    "SameNodeConnectionError",
    "NodeInputSerialization",
    "NodeOutputSerialization",
    "Node",
    "get_nodeclass",
    "run_until_complete",
    "NodeSpace",
    "FullNodeSpaceJSON",
    "NodeSpaceJSON",
    "FullLibJSON",
    "Shelf",
    "NodeJSON",
    "NodeClassMixin",
    "NodeDecorator",
    "Library",
    "find_shelf",
    "JSONEncoder",
    "JSONDecoder",
    "NodeClassNotFoundError",
    "FUNCNODES_LOGGER",
    "get_logger",
    "instance_nodefunction",
    "config",
    "RenderOptions",
    "NoValue",
    "DataEnum",
    "add_type",
    "types",
    "NodeIOSerialization",
    "lib",
    "nodemaker",
    "logging",
    "Encdata",
    "decorator",
    "setup",
    "NodeTriggerError",
]

__version__ = "0.4.9"

DEBUG = True
