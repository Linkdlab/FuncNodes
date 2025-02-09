from funcnodes_core import *  # noqa: F401, F403 # type: ignore
from funcnodes_core import __all__ as core_all  # Explicit import

from .worker import (
    FuncNodesExternalWorker,
    RemoteWorker,
    WSWorker,
    WorkerManager,
    assert_worker_manager_running,
)

from .patches import apply_patches

apply_patches()

__all__ = [
    "FuncNodesExternalWorker",
    "RemoteWorker",
    "WSWorker",
    "WorkerManager",
    "assert_worker_manager_running",
]

__all__ += core_all


__version__ = "0.5.33"
