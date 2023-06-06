from typing import Literal
import numpy as np


def reduce_to_min_length(*arrays):
    minlen = min(len(array) for array in arrays)
    return [array[:minlen] for array in arrays]


def sortxys(x, *ys):
    arrays = reduce_to_min_length(x, *ys)
    x = np.copy(arrays[0])
    ys = [np.copy(y) for y in arrays[1:]]
    sorted_indices = np.argsort(x)
    x = x[sorted_indices]
    ys = [y[sorted_indices] for y in ys]
    return [x, *ys]


def interpolate_xy(xin, yin, diff: Literal["min", "median", "mean", "max"] = "median"):
    # crop both arrays to the same length
    x, y = sortxys(xin, yin)

    x_diffs = np.diff(x)
    mindiff = np.min(x_diffs)
    maxdiff = np.max(x_diffs)
    if mindiff == maxdiff:
        return x, y

    if diff == "min":
        usediff = mindiff
    elif diff == "max":
        usediff = maxdiff
    elif diff == "median":
        usediff = np.median(x_diffs)
    elif diff == "mean":
        usediff = np.mean(x_diffs)
    else:
        raise ValueError(
            f"diff must be one of 'min', 'max', 'median', 'mean', not {diff}"
        )

    x_new = np.linspace(x[0], x[-1] + usediff, int(np.ceil((x[-1] - x[0]) / usediff)))
    y_new = np.interp(x_new, x, y)
    return x_new.astype(xin.dtype), y_new.astype(yin.dtype)
