from funcnodes_core import *  # noqa: F401, F403 # type: ignore
from funcnodes_core import __all__ as core_all  # Explicit import
from funcnodes_worker import *  # noqa: F401, F403 # type: ignore
from funcnodes_worker import __all__ as worker_all  # Explicit import
import sys

if sys.platform != "emscripten":
    from .worker import (  # noqa: F401
        WorkerManager,
        assert_worker_manager_running,
    )

    from .patches import apply_patches

    apply_patches()

    __all__ = [
        "WorkerManager",
        "assert_worker_manager_running",
    ]
else:
    __all__ = []

__all__ += worker_all + core_all


__version__ = "0.5.37"
