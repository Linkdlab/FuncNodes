from __future__ import annotations
from typing import (
    Optional,
    TypedDict,
    List,
    TYPE_CHECKING,
    Type,
    Any,
    TypeVar,
    Generic,
    Union,
    Tuple,
    Required,
    Callable,
    Dict,
    Literal,
)
from uuid import uuid4
from exposedfunctionality import FunctionInputParam, FunctionOutputParam
from exposedfunctionality.function_parser.types import type_to_string, string_to_type
from exposedfunctionality import serialize_type
from .eventmanager import (
    AsyncEventManager,
    MessageInArgs,
    emit_before,
    emit_after,
    EventEmitterMixin,
)
from .triggerstack import TriggerStack
from .utils.data import deep_fill_dict, deep_remove_dict_on_equal

from .utils.serialization import JSONEncoder, JSONDecoder
import json
import weakref
import enum

if TYPE_CHECKING:
    # Avoid circular import
    from .node import Node


class NodeIOSerialization(TypedDict):
    """Typing definition for serialized Node Input/Output serialization."""

    name: str
    description: Optional[str]
    type: str
    allow_multiple: Optional[bool]
    id: Required[str]
    value: Required[Any]
    is_input: bool
    render_options: IORenderOptions
    value_options: ValueOptions


class NodeInputSerialization(NodeIOSerialization, total=False):
    """Typing definition for serialized Node Input serialization."""

    required: bool
    does_trigger: bool
    default: Optional[Any]


class NodeOutputSerialization(NodeIOSerialization):
    """Typing definition for serialized Node Output serialization."""


class NodeIOClassSerialization(TypedDict, total=False):
    """Typing definition for serialized Node Input/Output class."""

    name: str
    description: Optional[str]
    type: str
    allow_multiple: Optional[bool]
    uuid: str


class FullNodeIOJSON(TypedDict):
    """Full JSON representation of a NodeIO."""

    id: str
    full_id: str | None
    name: str
    type: str
    is_input: bool
    connected: bool
    node: str | None
    value: Any
    does_trigger: bool
    render_options: IORenderOptions
    value_options: ValueOptions
    valuepreview_type: str


# A unique object that represents the absence of a value
class NoValueType:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NoValueType, cls).__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<NoValue>"

    def __str__(self):
        return "<NoValue>"


NoValue: NoValueType = NoValueType()


def NoValueEndocer(obj, preview=False):
    if obj is NoValue:
        return "<NoValue>", True
    return obj, False


def NoValueDecoder(obj):
    if obj == "<NoValue>":
        return NoValue, True
    return obj, False


JSONDecoder.add_decoder(NoValueDecoder)
JSONEncoder.add_encoder(NoValueEndocer)


class NodeIOError(Exception):
    """Base exception for Node Input/Output related errors."""


class NodeAlreadyDefinedError(NodeIOError):
    """Exception raised when a node is already defined for an NodeIO instance."""


class NodeConnectionError(NodeIOError):
    """Exception raised when an invalid connection is attempted."""


class SameNodeConnectionError(NodeConnectionError):
    """Exception raised when attempting to connect an IO to its own node."""


class MultipleConnectionsError(NodeConnectionError):
    """Exception raised when attempting to connect an IO that does not allow multiple connections."""


class NodeIOStatus(TypedDict):
    """Typing definition for Node Input status."""

    has_value: bool
    has_node: bool
    ready: bool
    connected: bool


class NodeInputStatus(NodeIOStatus):
    required: bool


class NodeOutputStatus(NodeIOStatus): ...


def raise_allow_connections(src: NodeIO, trg: NodeIO):
    """Checks and raises an exception if a connection between two NodeIO instances is not allowed.

    Args:
        src: The source NodeIO instance.
        trg: The target NodeIO instance.

    Returns:
        True if the connection is allowed, otherwise raises an exception.

    Raises:
        NodeConnectionError: If attempting to connect two outputs or two inputs.
        MultipleConnectionsError: If either the source or target does not allow multiple connections.
    """
    # Check if connection is not allowed between two outputs or two inputs
    if isinstance(src, NodeOutput):
        if not isinstance(trg, NodeInput):
            raise NodeConnectionError("Cannot connect two outputs")
    elif isinstance(src, NodeInput):
        if not isinstance(trg, NodeOutput):
            raise NodeConnectionError("Cannot connect two inputs")
    else:
        raise NodeConnectionError("Undefinable connection")

    # Check if connection would exceed allowed connections for source or target
    # the other node has to be removed first since in the connection process
    # a node might be added and then the check would fail in the creation of the reverse connection
    src_connections: List[NodeInput | NodeOutput] = list(src.connections)
    if trg in src_connections:
        src_connections.remove(trg)

    trg_connections: List[NodeInput | NodeOutput] = list(trg.connections)

    if src in trg_connections:
        trg_connections.remove(src)

    if len(src_connections) > 0 and not src.allow_multiple:
        raise MultipleConnectionsError(
            f"Source {src} already connected: {src_connections}"
        )

    if len(trg_connections) > 0 and not trg.allow_multiple:
        raise MultipleConnectionsError(
            f"Target {trg} already connected: {trg_connections}"
        )
    return True


class IORenderOptions(TypedDict, total=False):
    """Typing definition for Node Input/Output render options."""

    step: str
    preview_type: str
    type: str


class NumberValueOptions(TypedDict, total=False):
    """Typing definition for Node Input/Output number value options."""

    min: int
    max: int
    step: int


class EnumValueOptions(TypedDict, total=False):
    """Typing definition for Node Input/Output enum value options."""

    options: Dict[str, Union[int, str, float]]


class LiteralValueOptions(TypedDict, total=False):
    """Typing definition for Node Input/Output literal value options."""

    options: List[str, int, float]


ValueOptions = Union[NumberValueOptions, EnumValueOptions, LiteralValueOptions]


NodeIOType = TypeVar("NodeIOType")


class IOOptions(NodeIOSerialization, total=False):
    valuepreview_generator: Callable[[Any], Any]
    valuepreview_type: str
    emit_value_set: bool


class NodeInputOptions(IOOptions, NodeInputSerialization, total=False):
    pass


class NodeOutputOptions(IOOptions, NodeOutputSerialization, total=False):
    pass


def identity_preview_generator(value: Any) -> Any:
    return value


def generate_value_options(value_options, _type):
    if value_options is not None:
        return value_options

    opts = {}
    if isinstance(_type, dict) and "type" in _type and _type["type"] == "enum":
        opts["options"] = _type

    if isinstance(_type, dict) and "anyOf" in _type:
        nopts = {}
        for _t in _type["anyOf"]:
            nopts.update(generate_value_options(None, _t))
        opts = {**nopts, **opts}

    return opts


class NodeIO(EventEmitterMixin, Generic[NodeIOType]):
    """Abstract base class representing an input or output of a node in a node-based system."""

    default_allow_multiple = False

    def __init__(
        self,
        name: Optional[str] = None,
        type: str | Type = "Any",
        description: Optional[str] = None,
        allow_multiple: Optional[bool] = None,
        uuid: Optional[str] = None,
        id: Optional[str] = None,  # fallback for uuid
        render_options: Optional[IORenderOptions] = None,
        value_options: Optional[ValueOptions] = None,
        is_input: Optional[bool] = None,  # catch and ignore
        valuepreview_generator: Callable[[Any], Any] = identity_preview_generator,
        valuepreview_type: Optional[str] = None,
        emit_value_set: bool = True,
        #  **kwargs,
    ) -> None:
        """Initializes a new instance of NodeIO.

        Args:
            name: The name of the NodeIO.
            description: Optional description of the NodeIO.
        """
        super().__init__()

        if uuid is None and id is not None:
            uuid = id
        self._uuid = uuid or uuid4().hex
        self._name = name or self._uuid
        self._description = description
        self._value: Union[NodeIOType, NoValueType] = NoValue

        self._connected: List[NodeIO] = []
        self._allow_multiple: Optional[bool] = allow_multiple
        self._node: Optional[weakref.ref[Node]] = None
        if isinstance(type, str):
            type = string_to_type(type)
        if not isinstance(type, (str, dict)):
            type = serialize_type(type)
        self._typestr: Union[str, dict] = type

        self.eventmanager = AsyncEventManager(self)
        self._value_options: ValueOptions = {}
        self._default_render_options = render_options or {}
        self._default_value_options = generate_value_options(
            value_options, self._typestr
        )
        self._valuepreview_generator = valuepreview_generator
        self._valuepreview_type = valuepreview_type or self._typestr
        self._emit_value_set = emit_value_set

    def deserialize(self, data: NodeIOSerialization) -> None:
        if "name" in data:
            self._name = data["name"]
        if "description" in data:
            self._description = data["description"]
        if "id" in data:
            self._uuid = data["id"]
        if "value" in data:
            self._value = data["value"]

    def serialize(self) -> NodeIOSerialization:
        """Serializes the NodeIO instance to a dictionary.

        Returns:
            A dictionary containing the serialized name and description.
        """
        ser = NodeIOSerialization(
            name=self._name,
            type=self._typestr,
            id=self._uuid,
            is_input=self.is_input(),
            render_options=self.render_options,
            value_options=self.value_options,
        )
        if self._description is not None:
            ser["description"] = self._description
        if (
            self.allow_multiple is not None
            and self.allow_multiple is not self.default_allow_multiple
        ):
            ser["allow_multiple"] = self.allow_multiple

        return ser

    @property
    def name(self) -> str:
        """Gets the name of the NodeIO."""
        return self._name

    @property
    def uuid(self):
        """The unique identifier of the node."""
        return self._uuid

    @property
    def full_id(self) -> Optional[str]:
        if self.node is None:
            return None
        return f"{self.node.uuid}__{self.uuid}"

    @property
    def value(self) -> NodeIOType | NoValueType:
        """Gets the current value of the NodeIO."""
        return self._value

    @value.setter
    def value(self, value: NodeIOType) -> None:
        """Sets the value of the NodeIO."""
        self.set_value(value)

    @property
    def value_preview(self) -> str:
        """Gets a preview of the value of the NodeIO."""
        return self._valuepreview_generator(self.value)

    @property
    def valuepreview_type(self) -> str:
        return self._valuepreview_type

    @property
    def connections(self) -> List[NodeIO]:
        """Gets a list of NodeIO instances connected to this one."""
        return list(self._connected)

    def set_value(self, value: NodeIOType) -> None:
        """Sets the internal value of the NodeIO.

        Args:
            value: The value to set.
        """
        self._value = value

        if self._emit_value_set:
            msg = MessageInArgs(src=self)
            msg["result"] = self._valuepreview_generator(self.value)
            self.emit("after_set_value", msg=msg)
        return self.value

    @emit_before()
    @emit_after()
    def connect(self, other: NodeIO, replace: bool = False):
        """Connects this NodeIO instance to another NodeIO instance.

        Args:
            other: The NodeIO instance to connect to.
            replace: If True, existing connections will be replaced.

        Raises:
            NodeConnectionError: If the connection is not allowed.
        """
        if other in self._connected:
            return
        try:
            raise_allow_connections(self, other)
        except MultipleConnectionsError:
            if not replace:
                raise
            self.disconnect()

        self._connected.append(other)
        other.connect(self, replace=replace)
        self.post_connect(other)
        if self.is_input():
            src = other
            trg = self
        else:
            src = self
            trg = other

        return [
            src.node.uuid if src.node else None,
            src.uuid,
            trg.node.uuid if trg.node else None,
            trg.uuid,
        ]

    def c(self, *args, **kwargs):
        """Alias for connect."""
        return self.connect(*args, **kwargs)

    @emit_before()
    @emit_after()
    def disconnect(self, other: Optional[NodeIO] = None):
        """Disconnects this NodeIO instance from another NodeIO instance, or all if no specific one is provided.

        Args:
            other: The NodeIO instance to disconnect from. If None, disconnects from all.
        """
        if other is None:
            for other in self.connections:
                self.disconnect(other)
            return
        if other not in self._connected:
            return
        self._connected.remove(other)
        other.disconnect(self)
        return [
            self.node.uuid if self.node else None,
            self.uuid,
            other.node.uuid if other.node else None,
            other.uuid,
        ]

    def d(self, *args, **kwargs):
        """Alias for disconnect."""
        return self.disconnect(*args, **kwargs)

    def post_connect(self, other: NodeIO):
        """Called after a connection is made.

        Args:
            other: The NodeIO instance that was connected to.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self._name},{self.full_id})>"

    @property
    def node(self) -> Optional[Node]:
        """Gets the Node instance that this NodeIO belongs to."""
        return self._node() if self._node is not None else None

    @node.setter
    def node(self, node: Node) -> None:
        if self._node is not None:
            if self._node() is node:
                return
            raise NodeAlreadyDefinedError("NodeIO already belongs to a node")
        if node is not None:
            self._node = weakref.ref(node)
        else:
            self._node = None

    def ready(self) -> bool:
        return self.node is not None

    def status(self) -> NodeIOStatus:
        return NodeIOStatus(
            has_value=self.value is not NoValue,
            has_node=self.node is not None,
            ready=self.ready(),
            connected=len(self.connections) > 0,
        )

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        raise NotImplementedError()

    @property
    def does_trigger(self) -> bool:
        return True

    def serialize_class(self) -> NodeIOClassSerialization:
        ser = NodeIOClassSerialization(
            name=self.name,
            type=self._typestr,
            description=self._description,
            uuid=self.uuid,
        )
        if self._allow_multiple is not None:
            ser["allow_multiple"] = self._allow_multiple

        return ser

    def full_serialize(self) -> FullNodeIOJSON:
        """Generates a JSON serializable dictionary of the NodeIO.

        Returns
        -------
        FullNodeIOJSON:
            JSON serializable dictionary of the NodeIO
        """
        return FullNodeIOJSON(
            id=self.uuid,
            full_id=self.full_id,
            name=self.name,
            type=self._typestr,
            is_input=self.is_input(),
            connected=self.is_connected(),
            node=self.node.uuid if self.node else None,
            value=self.value_preview,
            valuepreview_type=self.valuepreview_type,
            does_trigger=self.does_trigger,
            render_options=self.render_options,
            value_options=self.value_options,
        )

    def _repr_json_(self) -> FullNodeIOJSON:
        return JSONEncoder.apply_custom_encoding(self.full_serialize())  # type: ignore

    @property
    def allow_multiple(self) -> bool:
        """
        Indicates whether this NodeInput allows multiple connections.

        Returns:
            A boolean indicating whether multiple connections are allowed.
            Defaults to False if not explicitly set.
        """
        return (
            self._allow_multiple
            if self._allow_multiple is not None
            else self.default_allow_multiple
        )

    @property
    def render_options(self) -> IORenderOptions:
        return self._default_render_options

    @property
    def value_options(self) -> ValueOptions:
        return deep_fill_dict(
            self._default_value_options,
            self._value_options,
            inplace=False,
            overwrite_existing=True,
        )

    @value_options.setter
    def value_options(self, value_options: ValueOptions):
        self._value_options = deep_remove_dict_on_equal(
            value_options, self._default_value_options, inplace=False
        )

    @emit_after()
    def update_value_options(self, **kwargs):
        deep_fill_dict(
            self._value_options, kwargs, inplace=True, overwrite_existing=True
        )

        return self.value_options

    def is_connected(self) -> bool:
        """Returns whether this NodeIO is connected to another NodeIO.

        Returns
        -------
        bool:
            whether this NodeIO is connected to another NodeIO
        """
        return len(self._connected) > 0


class NodeInput(NodeIO, Generic[NodeIOType]):
    """
    Represents an input connection point for a node in a node-based system.
    Inherits from NodeIO and represents a connection that can receive data.
    """

    default_does_trigger = True
    default_required = True
    default_allow_multiple = False

    def __init__(
        self,
        *args,
        does_trigger: Optional[bool] = None,
        required: Optional[bool] = None,
        default: Union[NodeIOType, NoValueType] = NoValue,
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of NodeInput.

        Accepts all arguments that NodeIO does.
        """

        self._does_trigger = (
            self.default_does_trigger if does_trigger is None else does_trigger
        )
        self.required = self.default_required if required is None else required
        super().__init__(*args, **kwargs)
        self._connected: List[NodeOutput] = self._connected
        self._default = default

    @property
    def value(self) -> NodeIOType | NoValueType:
        """Gets the current value of the NodeIO."""
        return self._value if self._value is not NoValue else self._default

    @value.setter
    def value(self, value: NodeIOType) -> None:
        """Sets the value of the NodeIO."""
        self.set_value(value)

    def set_default(self, default: NodeIOType | NoValueType):
        self._default = default

    @property
    def default(self) -> NodeIOType | NoValueType:
        return self._default

    @default.setter
    def default(self, default: NodeIOType | NoValueType):
        self.set_default(default)

    @classmethod
    def from_serialized_input(cls, serialized_input: FunctionInputParam) -> NodeInput:
        """
        Creates a NodeInput instance from serialized input data.

        Args:
            serialized_input: A dictionary containing serialized data for the node input.

        Returns:
            An instance of NodeInput initialized with the serialized data.
        """
        return cls(
            uuid=serialized_input["name"],
            description=serialized_input.get("description"),
            type=serialized_input["type"],
            allow_multiple=serialized_input.get("allow_multiple"),
            default=serialized_input.get("default", NoValue),
        )

    def serialize(self) -> NodeInputSerialization:
        """
        Serializes the NodeInput instance to a dictionary for storage or transmission.

        Returns:
            A dictionary containing the serialized name and description of the node input.
        """
        ser = NodeInputSerialization(
            **super().serialize(),
        )
        if self.required is not NodeInput.default_required:
            ser["required"] = self.required
        if self.does_trigger is not NodeInput.default_does_trigger:
            ser["does_trigger"] = self.does_trigger
        if self._default is not NoValue:
            ser["default"] = self._default
        return ser

    def to_dict(self) -> NodeInputOptions:
        ser: IOOptions = NodeInputOptions(
            valuepreview_generator=self._valuepreview_generator,
            valuepreview_type=self._valuepreview_type,
            **self.serialize(),
        )
        return ser

    def deserialize(self, data: NodeInputSerialization) -> None:
        super().deserialize(data)
        if "required" in data:
            self.required = data["required"]
        if "does_trigger" in data:
            self._does_trigger = data["does_trigger"]
        if "default" in data:
            self._default = data["default"]

    @classmethod
    def from_serialized_nodeio(
        cls, serialized_nodeio: NodeInputSerialization
    ) -> NodeInput:
        """
        Creates a NodeInput instance from serialized input data.

        Args:
            serialized_nodeio: A dictionary containing serialized data for the node input.

        Returns:
            An instance of NodeInput initialized with the serialized data.
        """

        ins = cls(**serialized_nodeio)
        ins.deserialize(serialized_nodeio)
        return ins

    def set_value(self, value: object, does_trigger: Optional[bool] = None) -> None:
        super().set_value(value)

        if self.node is not None:
            if does_trigger is None:
                does_trigger = self.does_trigger
            if does_trigger:
                self.node.request_trigger()

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        return True

    def ready(self):
        return super().ready() and (self.value is not NoValue or not self.required)

    def status(self) -> NodeInputStatus:
        return NodeInputStatus(required=self.required, **super().status())

    @property
    def connections(self) -> List[NodeOutput]:
        """Gets a list of NodeIO instances connected to this one."""
        return list(self._connected)

    @property
    def does_trigger(self) -> bool:
        """
        Indicates whether this NodeInput triggers the node when set.

        Returns:
            A boolean indicating whether the node is triggered when the input is set.
            Defaults to True if not explicitly set.
        """
        return self._does_trigger

    def trigger(self, triggerstack: Optional[TriggerStack] = None) -> TriggerStack:
        if triggerstack is None:
            triggerstack = TriggerStack()
        if not self.does_trigger or self.value is NoValue or self.node is None:
            return triggerstack

        return self.node.trigger(triggerstack=triggerstack)

    def __del__(self):
        self.disconnect()
        self._node = None
        self._value = NoValue


class NodeOutput(NodeIO):
    """
    Represents an output connection point for a node in a node-based system.
    Inherits from NodeIO and represents a connection that can send data.
    """

    default_allow_multiple = True

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes a new instance of NodeOutput.

        Accepts all arguments that NodeIO does.
        """

        super().__init__(*args, **kwargs)
        # self._connected: List[NodeInput] = self._connected

    @classmethod
    def from_serialized_output(
        cls, serialized_output: FunctionOutputParam
    ) -> NodeOutput:
        """
        Creates a NodeOutput instance from serialized output data.

        Args:
            serialized_output: A dictionary containing serialized data for the node output.

        Returns:
            An instance of NodeOutput initialized with the serialized data.
        """
        return cls(
            uuid=serialized_output["name"],
            description=serialized_output.get("description"),
            type=serialized_output["type"],
        )

    def serialize(self) -> NodeOutputSerialization:
        """
        Serializes the NodeOutput instance to a dictionary for storage or transmission.

        Returns:
            A dictionary containing the serialized name and description of the node output.
        """
        return NodeOutputSerialization(**super().serialize())

    def to_dict(self) -> NodeOutputOptions:
        ser: IOOptions = NodeOutputOptions(
            valuepreview_generator=self._valuepreview_generator,
            valuepreview_type=self.valuepreview_type,
            **self.serialize(),
        )
        return ser

    def deserialize(self, data: NodeIOSerialization) -> None:
        return super().deserialize(data)

    @classmethod
    def from_serialized_nodeio(
        cls, serialized_nodeio: NodeOutputSerialization
    ) -> NodeOutput:
        """
        Creates a NodeOutput instance from serialized output data.

        Args:
            serialized_nodeio: A dictionary containing serialized data for the node output.

        Returns:
            An instance of NodeOutput initialized with the serialized data.
        """
        ins = cls(**serialized_nodeio)
        ins.deserialize(serialized_nodeio)
        return ins

    @property
    def connections(self) -> List[NodeInput]:
        """Gets a list of NodeIO instances connected to this one."""
        return list(self._connected)

    def set_value(self, value: object, does_trigger: Optional[bool] = None) -> None:
        """Sets the internal value of the NodeIO.

        Args:
            value: The value to set.
        """
        super().set_value(value)
        for other in self.connections:
            other.set_value(value, does_trigger=does_trigger)

    def post_connect(self, other: NodeIO):
        """Called after a connection is made.

        Args:
            other: The NodeIO instance that was connected to.
        """
        if self.value is not NoValue:
            other.set_value(self.value)

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        return False

    def status(self) -> NodeOutputStatus:
        return NodeOutputStatus(**super().status())

    def trigger(self, triggerstack: Optional[TriggerStack] = None) -> TriggerStack:
        if triggerstack is None:
            triggerstack = TriggerStack()
        for connection in self.connections:
            connection.set_value(self.value)
            connection.trigger(triggerstack=triggerstack)
        return triggerstack
