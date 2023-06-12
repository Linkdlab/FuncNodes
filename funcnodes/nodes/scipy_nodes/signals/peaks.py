from funcnodes.nodespace import LibShelf
from funcnodes.nodes.numpy_nodes.types import NdArrayType
from funcnodes.node import Node, NodeInput, NodeOutput
import numpy as np
from scipy.signal import find_peaks_cwt, find_peaks
from scipy.integrate import simps
from .signal_tools import interpolate_xy
import pandas as pd
from funcnodes.nodes.pandas_nodes.types import DataFrameType


class FindPeaksCWT(Node):
    node_id = "scipy.signal.find_peaks_cwt"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    widths = NodeInput(type=NdArrayType, required=True)

    output = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        y = self.y.value
        if len(y) <= 1:
            self.output.value = np.array([])
            return True
        x = self.x.value_or_none

        if x is not None:
            if len(x) <= 1:
                self.output.value = np.array([])
                return True
            x, y = interpolate_xy(self.x.value, y)
        else:
            x = np.arange(len(y))

        peaks = find_peaks_cwt(y, self.widths.value)
        if len(peaks) == 0:
            self.output.value = np.array([])
            return True

        peaks = x[peaks]

        self.output.value = peaks
        return True


class FindPeaks(Node):
    node_id = "scipy.signal.find_peaks"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    min_distance = NodeInput(type=float, default_value=0)
    min_width = NodeInput(type=float, default_value=0)
    min_height = NodeInput(type=float, default_value=0)

    peak_indices = NodeOutput(type=NdArrayType)

    async def on_trigger(self):
        y = self.y.value
        if len(y) <= 1:
            self.peak_indices.value = np.array([])
            return True
        x = self.x.value_or_none

        if x is not None:
            if len(x) <= 1:
                self.peak_indices.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        diffx = np.diff(x)
        if np.all(diffx == 0):
            raise ValueError("dx is all zero")
        dx = diffx.min()

        if dx <= 0:
            dx = np.median(diffx)

        if dx <= 0:
            dx = diffx.mean()

        min_distance = self.min_distance.value
        min_distance = int(dx / max(dx, min_distance))
        if min_distance <= 1:
            min_distance = 1

        min_width = self.min_width.value
        min_width = int(dx / max(dx, min_width))
        if min_width <= 1:
            min_width = None

        min_height = self.min_height.value
        if min_height <= 0:
            min_height = None

        peaks, _ = find_peaks(
            y, distance=min_distance, width=min_width, height=min_height
        )

        self.peak_indices.value = peaks

        return True


class FindPeaksAndEval(Node):
    node_id = "scipy.signal.find_peaks_and_eval"
    x = NodeInput(type=NdArrayType)
    y = NodeInput(type=NdArrayType, required=True)
    min_distance = NodeInput(type=float, default_value=0)
    min_width = NodeInput(type=float, default_value=0)
    min_height = NodeInput(type=float, default_value=0)
    rel_peak_end = NodeInput(type=float, default_value=0.05)

    peak_indices = NodeOutput(type=NdArrayType)
    peak_data = NodeOutput(type=DataFrameType)

    async def on_trigger(self):
        y = self.y.value
        if len(y) <= 1:
            self.peak_indices.value = np.array([])
            return True
        x = self.x.value_or_none

        if x is not None:
            if len(x) <= 1:
                self.peak_indices.value = np.array([])
                return True
            x, y = interpolate_xy(x, y)
        else:
            x = np.arange(len(y))

        diffx = np.diff(x)
        if np.all(diffx == 0):
            raise ValueError("dx is all zero")
        dx = diffx.min()

        if dx <= 0:
            dx = np.median(diffx)

        if dx <= 0:
            dx = diffx.mean()

        min_distance = self.min_distance.value
        min_distance = int(dx / max(dx, min_distance))
        if min_distance <= 0:
            min_distance = 1

        min_width = self.min_width.value
        min_width = int(dx / max(dx, min_width))
        if min_width <= 1:
            min_width = None

        min_height = self.min_height.value
        if min_height <= 0:
            min_height = None

        peaks, _ = find_peaks(
            y, distance=min_distance, width=min_width, height=min_height
        )

        self.peak_indices.value = peaks

        y_norm = y - y.min()
        y_norm = y_norm / y_norm.max()

        peakdata = {}
        peakdata["left_by_next_peak"] = np.concatenate([[0], peaks[:-1]])
        peakdata["right_by_next_peak"] = np.concatenate([peaks[1:], [len(y_norm) - 1]])

        rel_peak_end = self.rel_peak_end.value

        peakdata["left_by_rel_height"] = np.zeros_like(peaks)
        peakdata["right_by_rel_height"] = np.ones_like(peaks) * len(y_norm)
        for pi, p in enumerate(peaks):
            peak_th = y_norm[p] * rel_peak_end

            left_data = y_norm[:p]
            allowed_left = left_data < peak_th
            if allowed_left.any():
                peakdata["left_by_rel_height"][pi] = np.where(allowed_left)[0][-1]

            right_data = y_norm[p:]
            allowed_right = right_data < peak_th
            if allowed_right.any():
                peakdata["right_by_rel_height"][pi] = np.where(allowed_right)[0][0] + p

        peakdata["left"] = np.maximum(
            peakdata["left_by_next_peak"], peakdata["left_by_rel_height"]
        )
        peakdata["right"] = np.minimum(
            peakdata["right_by_next_peak"], peakdata["right_by_rel_height"]
        )

        peakdata["left_by_overlap"] = np.zeros_like(peaks)
        peakdata["right_by_overlap"] = np.ones_like(peaks) * len(y_norm)
        for pi, p in enumerate(peaks):
            # left
            if pi > 0:
                left_peak_right = peakdata["right"][pi - 1]
                peak_left = peakdata["left"][pi]
                if left_peak_right > peak_left:
                    overlap_min = (
                        np.argmin(y_norm[peak_left:left_peak_right]) + peak_left
                    )
                    peakdata["left_by_overlap"][pi] = overlap_min
                    peakdata["right_by_overlap"][pi - 1] = overlap_min

        peakdata["left"] = np.maximum(peakdata["left"], peakdata["left_by_overlap"])
        peakdata["right"] = np.minimum(peakdata["right"], peakdata["right_by_overlap"])

        peakdata["left_by_min"] = np.zeros_like(peaks)
        peakdata["right_by_min"] = np.ones_like(peaks) * len(y_norm)

        for pi, p in enumerate(peaks):
            subpeakdata = y_norm[peakdata["left"][pi] : peakdata["right"][pi]]
            pn = p - peakdata["left"][pi]
            peakdata["left_by_min"][pi] = (
                np.argmin(subpeakdata[:pn]) + peakdata["left"][pi]
            )
            peakdata["right_by_min"][pi] = (
                np.argmin(subpeakdata[pn:]) + peakdata["left"][pi] + pn
            )

        peakdata["left"] = np.maximum(peakdata["left"], peakdata["left_by_min"])
        peakdata["right"] = np.minimum(peakdata["right"], peakdata["right_by_min"])

        peakdata["FWHM_left"] = np.zeros_like(peaks) * np.nan
        peakdata["FWHM_right"] = np.zeros_like(peaks) * np.nan
        peakdata["W10_left"] = np.zeros_like(peaks) * np.nan
        peakdata["W10_right"] = np.zeros_like(peaks) * np.nan

        for pi, p in enumerate(peaks):
            subpeakdata = y_norm[peakdata["left"][pi] : peakdata["right"][pi]]
            pn = p - peakdata["left"][pi]
            subpeakdata = subpeakdata - subpeakdata.min()
            subpeakdata = subpeakdata / subpeakdata.max()

            th = 0.5
            if pn > 0:
                left = np.argmin(np.abs(subpeakdata[:pn] - th)) + peakdata["left"][pi]
            else:
                left = peakdata["left"][pi]

            if pn < len(subpeakdata) - 1:
                right = (
                    np.argmin(np.abs(subpeakdata[pn:] - th)) + pn + peakdata["left"][pi]
                )
            else:
                right = peakdata["right"][pi]

            peakdata["FWHM_left"][pi] = left
            peakdata["FWHM_right"][pi] = right

            th = 0.1

            if pn > 0:
                left = np.argmin(np.abs(subpeakdata[:pn] - th)) + peakdata["left"][pi]
            else:
                left = peakdata["left"][pi]

            if pn < len(subpeakdata) - 1:
                right = (
                    np.argmin(np.abs(subpeakdata[pn:] - th)) + pn + peakdata["left"][pi]
                )
            else:
                right = peakdata["right"][pi]

            peakdata["W10_left"][pi] = left
            peakdata["W10_right"][pi] = right

        fwhm_nan = np.isnan(peakdata["FWHM_left"]) | np.isnan(peakdata["FWHM_right"])

        peakdata["FWHM"] = np.zeros_like(peaks) * np.nan
        peakdata["W10"] = np.zeros_like(peaks) * np.nan
        w10_nan = np.isnan(peakdata["W10_left"]) | np.isnan(peakdata["W10_right"])
        peakdata["FWHM"][~fwhm_nan] = (
            x[peakdata["FWHM_right"][~fwhm_nan].astype(int)]
            - x[peakdata["FWHM_left"][~fwhm_nan].astype(int)]
        )
        peakdata["W10"][~w10_nan] = (
            x[peakdata["W10_right"][~w10_nan].astype(int)]
            - x[peakdata["W10_left"][~w10_nan].astype(int)]
        )

        peakdata["area"] = np.zeros_like(peaks, dtype=float)
        for pi, p in enumerate(peaks):
            left = peakdata["left"][pi]
            right = peakdata["right"][pi]
            peakdata["area"][pi] = simps(y[left:right], x=x[left:right])

        peakdata["norm_area"] = peakdata["area"] / peakdata["area"].max()
        peakdata["rel_area"] = peakdata["norm_area"] / peakdata["norm_area"].sum()
        peakdata["x"] = x[peaks]
        peakdata["leftx"] = x[peakdata["left"]]
        peakdata["rightx"] = x[peakdata["right"]]
        peakdata["peak_heights"] = y[peaks]

        self.peak_data.value = pd.DataFrame(peakdata)


LIB = LibShelf(
    name="peaks",
    nodes=[FindPeaksCWT],
    shelves=[],
)
