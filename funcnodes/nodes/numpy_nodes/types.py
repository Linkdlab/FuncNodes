import numpy as np
from numpy import typing as npt
from typing import Any, Type
from ...iotypes import IOType, IOTypesError, indentity


class ArrayLikeType(IOType):
    typestring: str = "np.arraylike"
    typeclass = (bool, int, float, complex, str, bytes, np.ndarray)

    @classmethod
    def cast(cls, value: Any) -> Any:
        return np.array(value)

    @classmethod
    def equal(cls, a: np.ndarray, b: np.ndarray) -> bool:
        return np.array_equal(a, b)


IOType.register_type(npt.ArrayLike, ArrayLikeType)
IOType.register_cross_caster(
    ArrayLikeType,
    int,
    lambda x: int(np.array(x, dtype=int).reshape(-1)[0]),
    lambda x: np.array(x).reshape(-1),
)
IOType.register_cross_caster(
    ArrayLikeType,
    bool,
    lambda x: bool(np.array(x, dtype=bool).reshape(-1)[0]),
    lambda x: np.array(x).reshape(-1),
)
IOType.register_cross_caster(
    ArrayLikeType,
    float,
    lambda x: float(np.array(x, dtype=float).reshape(-1)[0]),
    lambda x: np.array(x).reshape(-1),
)

IOType.register_cross_caster(
    ArrayLikeType,
    list,
    lambda x: np.array(x).tolist(),
    indentity,
)


class NdArrayType(ArrayLikeType):
    typeclass = (np.ndarray,)
    typestring: str = "np.ndarray"


IOType.register_cross_caster(ArrayLikeType, NdArrayType, np.array, indentity)
IOType.register_cross_caster(NdArrayType, "json", lambda x: x.tolist())
IOType.register_cross_caster(NdArrayType, list, lambda x: x.tolist(), np.array)


class NpNumberType(ArrayLikeType):
    typeclass = np.number
    typestring: str = "np.number"


IOType.register_cross_caster(NpNumberType, ArrayLikeType, indentity)

for n in dir(np):
    v = getattr(np, n)
    if (
        isinstance(v, type)
        and issubclass(v, np.generic)
        and v is not np.generic
        and v is not np.number
    ):
        t = type(n, (NpNumberType,), {"typeclass": (v,), "typestring": f"np.{n}"})
        IOType.register_cross_caster(t, NpNumberType, indentity, v)


def ndarray_type_creator(dtype=None, shape=None) -> Type[NdArrayType]:
    ts = NdArrayType.typestring
    if dtype is not None:
        ts += f"[{dtype}]"
    if shape is not None:
        ts += f"({shape})"

    try:
        return IOType.get_type(ts)
    except IOTypesError:
        pass

    class _NdArrayType(NdArrayType):
        typestring: str = ts

    IOType.register_type(ts, _NdArrayType)

    def _caster(value: np.ndarray) -> np.ndarray:
        if dtype is not None:
            value = value.astype(dtype)
        if shape is not None:
            value = value.reshape(shape)
        return value

    IOType.register_cross_caster(_NdArrayType, NdArrayType, indentity, _caster)

    return _NdArrayType
