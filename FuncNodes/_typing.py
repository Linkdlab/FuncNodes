"""typings used in the project"""
from __future__ import annotations
import sys

if sys.version_info < (3, 11):
    from typing_extensions import Required, TypedDict, Unpack, NotRequired
else:
    from typing import Required, NotRequired, TypedDict, Unpack

from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Protocol, Generic


if TYPE_CHECKING:
    from .node import Node
    from .nodespace import NodeSpace
    from .io import NodeIO, Edge
    from .mixins import EventEmitterMixin

# region Events


class MessageInArgs(TypedDict):
    src: NotRequired[EventEmitterMixin]


GenericMessageInArgs = TypeVar("GenericMessageInArgs", bound=MessageInArgs)


class EventCallback(Protocol, Generic[GenericMessageInArgs]):
    def __call__(self, **kwargs: Unpack[GenericMessageInArgs]) -> Any:  # type: ignore
        ...


class EventErrorCallback(Protocol):
    def __call__(self, error: Exception, src: Any) -> Any:
        ...


# endregion Events

# region Node

NodeDataName = str

NodeIdType = str


class PropIODict(TypedDict, total=False):
    """TypedDict for NodeProperties.io"""

    ip: Dict[NodeIOId, IOProperties]
    op: Dict[NodeIOId, IOProperties]


class NodeStatus(TypedDict):
    """TypedDict for Node status"""

    disabled: bool
    miss_inputs: List[NodeIOId]
    miss_data: List[NodeDataName]
    operable: bool
    ready: bool
    is_working: bool
    has_trigger_request: bool


class NodeStateInterface(TypedDict):
    """TypedDict for Node.state"""

    inputs: Dict[NodeIOId, NodeIOState]
    outputs: Dict[NodeIOId, NodeIOState]
    data: Dict[NodeDataName, Any]
    status: NodeStatus


class Message_Node_SetData(MessageInArgs):
    """Message for Node.setData"""

    name: NodeDataName
    old: Any
    new: Any


class Message_Node_SetName(MessageInArgs):
    name: NodeDataName


class Message_Node_CheckStatus(MessageInArgs, NodeStatus):
    """Message for Node.checkStatus"""


class Message_Node_Disconnected(MessageInArgs):
    edge: Edge


class Message_Node_TriggerError(MessageInArgs):
    msg: str


class Message_Node_NewConnection(MessageInArgs):
    """Type definition for the node message when a new connection is created."""

    edge: Edge


class Message_Node_SetNodeSpace(MessageInArgs):
    nodespace: NodeSpace


class Message_Node_AddIO(MessageInArgs):
    io: NodeIO


class Message_Node_AddInput(MessageInArgs):
    node_input: NodeIO


class Message_Node_AddOutput(MessageInArgs):
    node_output: NodeIO


class Message_Node_RemoveIO(MessageInArgs):
    io: NodeIO


# endregion Node


# region NodeIO

NodeIOId = str


class Message_NodeIO_Connected(MessageInArgs):
    to: NodeIO


class Message_NodeIO_Disconnected(MessageInArgs):
    other: NodeIO


class IOProperties(TypedDict, total=False):
    """Type definition for the minimal properties of a NodeIO."""

    id: NodeIOId
    type: str
    required: bool | None
    default_value: Any | None
    allows_multiple: bool
    does_trigger: bool
    trigger_on_get: bool


class NodeIOState(TypedDict):
    """Type definition for the state of a NodeIO."""

    properties: IOProperties


# endregion NodeIO


# region NodeSpace


class LibShelf(TypedDict):
    name: str
    nodes: List[Type[Node]]
    shelves: List[LibShelf]


class Message_NodeSpace_AddNode(MessageInArgs):
    node: Node


class Message_NodeSpace_RemoveNode(MessageInArgs):
    node: Node


class Message_NodeSpace_AddEdge(MessageInArgs):
    edge: Edge


class Message_NodeSpace_RemoveEdge(MessageInArgs):
    edge: Edge


# endregion NodeSpace
