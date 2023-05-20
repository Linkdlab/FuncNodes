from typing import Any
import pandas as pd
from ...iotypes import IOType, JSONType
from ..numpy_nodes.types import NdArrayType


class DataFrameType(IOType):
    typestring: str = "pd.DataFrame"
    typeclass: Any = pd.DataFrame

    @classmethod
    def equal(cls, a: Any, b: Any) -> bool:
        if not isinstance(a, pd.DataFrame):
            return False
        if not isinstance(b, pd.DataFrame):
            return False
        return a.equals(b)


def json_to_dataframe(value: dict) -> pd.DataFrame:
    if "index" in value and "columns" in value and "data" in value:
        return pd.DataFrame.from_dict(value, orient="tight")
    return pd.DataFrame.from_dict(value)


IOType.register_cross_caster(
    DataFrameType,
    JSONType,
    lambda x: x.to_dict(orient="split"),
    json_to_dataframe,
)

IOType.register_cross_caster(
    DataFrameType.typestring,
    NdArrayType.typestring,
    lambda x: x.to_numpy(copy=True),
    lambda x: pd.DataFrame(x),
)


class SeriesType(IOType):
    typestring: str = "pd.Series"
    typeclass: Any = pd.Series

    @classmethod
    def equal(cls, a: Any, b: Any) -> bool:
        if not isinstance(a, pd.Series):
            return False
        if not isinstance(b, pd.Series):
            return False
        return a.equals(b)


IOType.register_cross_caster(
    SeriesType,
    DataFrameType,
    lambda x: x.to_frame(),
    lambda x: x.iloc[:, 0].squeeze(),
)

IOType.register_cross_caster(
    SeriesType,
    list,
    lambda x: x.tolist(),
    pd.Series,
)
