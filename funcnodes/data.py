from __future__ import annotations
import enum
from exposedfunctionality.function_parser.types import add_type
from typing import Union, Any, TypeVar, Type, Generic


ET = TypeVar("ET", bound="DataEnum")


class DataEnum(enum.Enum):
    """
    Base class for data enums. They should be used as a type hint for a function argument for funcnodes.
    In the function the value can be accessed by using the v method.
    The reson for this is to be more robust that the values to the function can be
    passed as the Enum, as a value or as a enum key.

    Example:
    ```python
    class TestEnum(DataEnum):
        A = 1
        B = 2
        C = 3

    @NodeDecorator(node_id="test_enum")
    def test_enum_node(a: TestEnum) -> int:
        a = TestEnum.v(a)
        return a
    """

    def __init_subclass__(cls) -> None:
        add_type(
            cls,
            cls.__name__,
        )

    @classmethod
    def interfere(cls: Type[ET], a: Union[ET, str, Any]) -> ET:
        if isinstance(a, str) and a in cls.__members__:
            return cls[a]
        elif isinstance(a, cls):
            return a
        else:
            return cls(a)

    @classmethod
    def v(cls: Type[ET], a: Union[ET, str, Any]) -> Any:
        return cls.interfere(a).value
