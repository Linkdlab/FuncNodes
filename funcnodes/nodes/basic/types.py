import datetime

try:
    import numpy as np

    dt_type = np.ndarray
    from funcnodes.nodes.numpy_nodes.types import NdArrayType  # noqa

    def now_getter():
        return np.datetime64(datetime.now())

except ImportError:
    dt_type = datetime
    now_getter = datetime.now
