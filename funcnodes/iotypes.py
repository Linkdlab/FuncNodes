from __future__ import annotations
from typing import Any, Dict, Callable, List, Tuple, Type
import json
import io
import networkx as nx
import datetime
import logging

logger = logging.getLogger("funcnodes")


def indentity(x: Any) -> Any:
    return x


class IOTypesError(Exception):
    pass


class IOType:
    _types: Dict[Any, Type[IOType]] = {}
    _cross_caster: Dict[Type[IOType], Dict[Type[IOType], Callable[[Any], Any]]] = {}
    _type_graph: nx.DiGraph = nx.DiGraph()
    typeclass: Tuple[Any, ...] = ()
    typestring: str = None  # type: ignore
    additional_types: List[Any] = []
    _cached_castings: Dict[Any, Dict[Any, Callable[[Any], Any]]] = {}

    @staticmethod
    def register_type(typeid: Any, io_type: Type[IOType]):
        """This method registers
        a new IOType object for a given type. It takes two parameters, type
        which is the Python type to register, and io_type which is the
        IOType object to associate with the type. It first checks if the
        type is already registered, and raises an exception if it is.
        Then it adds the new type and IOType object to the _types dictionary,
        with the type as the key and the IOType object as the value.
        It also adds the type string of the IOType object to the _types
        dictionary,with the type string as the key and the IOType
        object as the value."""
        if typeid in IOType._types:
            if IOType._types[typeid] != io_type:
                logger.error(
                    "IOType %s is already registered "
                    "as %s and cannot be registered as %s",
                    typeid,
                    IOType._types[typeid],
                    io_type,
                )
            return
        IOType._types[typeid] = io_type
        if io_type.typeclass not in IOType._types:
            IOType._types[io_type.typeclass] = io_type

        for tc in io_type.typeclass:
            if tc not in IOType._types:
                IOType._types[tc] = io_type

        for additional_type in IOType._types[typeid].additional_types:
            if additional_type in IOType._types:
                raise IOTypesError(f"IOType {additional_type} is already registered")
            IOType._types[additional_type] = io_type

        IOType._type_graph.add_node(io_type.typestring)
        IOType._cross_caster[io_type] = {}

    def __init_subclass__(cls):
        if not isinstance(cls.typeclass, tuple):
            cls.typeclass = (cls.typeclass,)
        IOType.register_type(cls.typestring, cls)

    @staticmethod
    def register_cross_caster(
        from_type: str | Type[IOType] | Any,
        to_type: str | Type[IOType] | Any,
        caster: Callable[[Any], Any],
        reverse: Callable[[Any], Any] | None = None,
    ):
        """This method registers a type caster function for converting from
        one type to another. It takes three parameters: from_type which is
        the string representation of the input type, to_type which is the
        string representation of the output type, and caster which is a
        callable that takes an input value and returns the output value.
        It first checks if the input type is already in the cross_caster
        dictionary. If it's not, it creates a new dictionary for the input
        type. Then it adds the type caster function to the dictionary,
        with the output type as the key and the function as the value."""

        if (not isinstance(from_type, type)) or (not issubclass(from_type, IOType)):
            from_type = IOType.get_type(from_type)
        if (not isinstance(to_type, type)) or (not issubclass(to_type, IOType)):
            to_type = IOType.get_type(to_type)

        IOType._cross_caster[from_type][to_type] = caster
        IOType._type_graph.add_edge(
            from_type.typestring, to_type.typestring, caster=caster
        )
        IOType._cached_castings = {}
        if reverse is not None:
            IOType.register_cross_caster(to_type, from_type, reverse)

    @staticmethod
    def get_type(vartype: Any) -> Type[IOType]:
        """This method returns the IOType object associated with a given
        Python type. It takes one parameter, type which is the Python
        type to retrieve the IOType object for. If the type is not registered,
        it raises an exception. If the type is registered,
        it returns the corresponding IOType object."""
        if isinstance(vartype, type):
            if issubclass(vartype, IOType):
                return vartype
        if vartype not in IOType._types:
            if str(vartype) in IOType._types:
                return IOType._types[str(vartype)]

            if hasattr(vartype, "__module__"):
                mod = vartype.__module__
            else:
                mod = "unknown"
            raise IOTypesError(
                f"IOType {vartype} is not registered (type from module: {mod})"
            )
        return IOType._types[vartype]

    @staticmethod
    def get_casting_path(
        from_type: str | Type[IOType] | Any,
        to_type: str | Type[IOType] | Any,
    ) -> List[Type[IOType]]:
        """This method returns the shortest casting path between two types on
        the directed graph. It takes two parameters: from_type which is the
        string representation of the input type or the type itself, to_type
        which is the string representation of the output type or the
        type itself. If the path is not available, it raises an
        exception. If the path is available, it returns the corresponding
        list of Type[IOType] objects."""

        if (not isinstance(from_type, type)) or (not issubclass(from_type, IOType)):
            io_from_type = IOType.get_type(from_type)
        else:
            io_from_type = from_type

        if (not isinstance(to_type, type)) or (not issubclass(to_type, IOType)):
            io_to_type = IOType.get_type(to_type)
        else:
            io_to_type = to_type

        try:
            path = nx.shortest_path(
                IOType._type_graph, io_from_type.typestring, io_to_type.typestring
            )
        except nx.NetworkXNoPath as err:
            raise IOTypesError(
                f"No casting path from {from_type} to {to_type} available"
            ) from err

        # Get the caster functions associated with each edge in the path
        iopath = []
        for i in range(len(path)):
            iot = IOType.get_type(path[i])
            iopath.append(iot)

        return iopath

    @classmethod
    def create_casting_from_to(cls, to_type: Type[IOType]):
        path = IOType.get_casting_path(cls, to_type)

        def _create_func(p):
            crosscaster = [
                IOType._cross_caster[p[i]][p[i + 1]] for i in range(len(p) - 1)
            ]

            def _cast(value):
                for caster in crosscaster:
                    value = caster(value)
                return value

            return _cast

        f = _create_func(path)
        if cls not in IOType._cached_castings:
            IOType._cached_castings[cls] = {}
        IOType._cached_castings[cls] = {to_type: f}

    @classmethod
    def create_casting_from(cls, from_type: Type[IOType]):
        return from_type.create_casting_from_to(cls)

    @classmethod
    def cast_if_needed(cls, value: Any) -> Any:
        """cehcks whether the value is of the correct type and casts it if not"""
        if not cls.typecheck(value):
            return cls.cast_value(value)

        return value

    @classmethod
    def typecheck(cls, value: Any) -> bool:
        """checks whether the value is of the correct type"""
        return isinstance(value, cls.typeclass)

    @classmethod
    def cast_value(cls, value: Any) -> Any:
        """casts the value to the correct type"""

        valuetype = cls.get_type(type(value))
        if valuetype not in IOType._cached_castings:
            cls.create_casting_from(valuetype)
        else:
            if cls not in IOType._cached_castings[valuetype]:
                cls.create_casting_from(valuetype)

        casting = IOType._cached_castings[valuetype][cls]
        return casting(value)

    @classmethod
    def equal(cls, a: Any, b: Any) -> bool:
        return a == b

    @classmethod
    def cast(cls, value: Any) -> Any:
        return value


class AnyType(IOType):
    typeclass = (object,)
    typestring: str = "any"
    additional_types = [Any]


class IntType(IOType):
    typeclass = (int,)
    typestring: str = "int"

    @classmethod
    def cast(cls, value: Any) -> Any:
        return int(value)


class FloatType(IOType):
    typeclass = (float,)
    typestring: str = "float"

    @classmethod
    def cast(cls, value: Any) -> Any:
        return float(value)


class BoolType(IOType):
    typeclass = (bool,)
    typestring: str = "bool"

    @classmethod
    def cast(cls, value: Any) -> Any:
        return bool(value)


IOType.register_cross_caster(IntType, FloatType, float, int)
IOType.register_cross_caster(IntType, BoolType, bool, int)
IOType.register_cross_caster(FloatType, BoolType, bool, float)


class StrType(IOType):
    typeclass = (str,)
    typestring: str = "str"

    @classmethod
    def cast(cls, value: Any) -> Any:
        return str(value)


class ByteType(IOType):
    typeclass = (bytes,)
    typestring: str = "bytes"

    @classmethod
    def cast(cls, value: Any) -> Any:
        return bytes(value)


IOType.register_cross_caster(FloatType, StrType, str)
IOType.register_cross_caster(BoolType, StrType, str)
IOType.register_cross_caster(IntType, StrType, str)

IOType.register_cross_caster(
    ByteType.typestring,
    StrType.typestring,
    lambda x: x.decode("utf-8", errors="ignore"),
    lambda x: x.encode("utf-8", errors="ignore"),
)


class JSONType(IOType):
    typeclass = (dict,)
    typestring: str = "json"
    additional_types: List[Any] = [json]

    @classmethod
    def cast(cls, value: Any) -> Any:
        return json.loads(json.dumps(value))

    @classmethod
    def typecheck(cls, value: Any) -> bool:
        return False
        try:
            json.dumps(value)
            return True
        except TypeError:
            return False


IOType.register_cross_caster(JSONType, FloatType, float, indentity)
IOType.register_cross_caster(JSONType, IntType, int, indentity)
IOType.register_cross_caster(JSONType, BoolType, bool, indentity)
IOType.register_cross_caster(JSONType, StrType, json.dumps, indentity)


class ListType(IOType):
    typeclass = (list,)
    typestring: str = "list"


IOType.register_cross_caster(IntType, ListType, lambda x: [x])
IOType.register_cross_caster(FloatType, ListType, lambda x: [x])
IOType.register_cross_caster(BoolType, ListType, lambda x: [x])
IOType.register_cross_caster(StrType, ListType, list)
IOType.register_cross_caster(ByteType, ListType, list)


class BytesIOType(IOType):
    typeclass = (io.BytesIO,)
    typestring: str = "BytesIO"


IOType.register_cross_caster(
    BytesIOType, ByteType, lambda x: x.read(), lambda x: io.BytesIO(x)
)


class DateTimeType(IOType):
    typeclass = (datetime.datetime,)
    typestring: str = "datetime"


IOType.register_cross_caster(
    DateTimeType,
    StrType,
    lambda x: x.isoformat(),
    lambda x: datetime.datetime.fromisoformat(x),
)

IOType.register_cross_caster(
    DateTimeType,
    FloatType,
    lambda x: x.timestamp(),
    lambda x: datetime.datetime.fromtimestamp(x),
)
