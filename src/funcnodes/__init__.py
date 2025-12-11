from funcnodes_core import *  # noqa: F401, F403 # type: ignore
from funcnodes_core import __all__ as core_all  # Explicit import
from funcnodes_worker import *  # noqa: F401, F403 # type: ignore
from funcnodes_worker import __all__ as worker_all  # Explicit import
import sys
from .utils.lazy import LazyImport
from importlib.metadata import version, PackageNotFoundError

if sys.platform != "emscripten":
    from .worker import (  # noqa: F401
        WorkerManager,
        assert_worker_manager_running,
    )

    from .patches import apply_patches

    apply_patches()

    __all__ = [
        "LazyImport",
        "WorkerManager",
        "assert_worker_manager_running",
    ]
else:
    __all__ = ["LazyImport"]

__all__ += worker_all + core_all


try:
    __version__ = version("funcnodes")
except PackageNotFoundError:
    # Package isn't installed (e.g. during local dev)
    __version__ = "0.0.0"
