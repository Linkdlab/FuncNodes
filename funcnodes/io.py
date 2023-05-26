"""
Module for Node inputs and outputs.
"""
from __future__ import annotations
from typing import Any, List, Tuple, TYPE_CHECKING, TypeVar, TypedDict, NamedTuple, cast

import uuid
import copy
from .iotypes import IOType
from .utils import deep_remove_dict_on_equal
from .mixins import (
    EventEmitterMixin,
    ObjectLoggerMixin,
)
from .errors import NodeIOError, EdgeError, MissingValueError, NodeError
from ._typing import (
    NodeIOId,
    NodeIOState,
    Message_Node_NewConnection,
    IOProperties,
    Message_NodeIO_Connected,
    Message_NodeIO_Disconnected,
    Message_Node_Disconnected,
    MessageInArgs,
    NodeIdType,
    FixedIOProperties,
)
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .node import Node, TriggerQueue

from functools import wraps
import json

try:
    import numpy as np
except ImportError:
    np = None

UNDEFINED = object()


def cached_call(name):
    cache_name = f"__{name}_cached"

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, cache_name):
                setattr(self, cache_name, func(self, *args, **kwargs))
            return getattr(self, cache_name)

        return wrapper

    return decorator


def resets_cache(name):
    cache_name = f"__{name}_cached"

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, cache_name):
                delattr(self, cache_name)
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def reset_cache(self, name):
    cache_name = f"__{name}_cached"
    if hasattr(self, cache_name):
        delattr(self, cache_name)


class Message_NodeIO_ValueChanged(MessageInArgs):
    """Message for NodeIO.value_changed event."""

    old: Any
    new: Any


def reduce_list(lst: list) -> list:
    if len(lst) > 20:
        return (
            [reduce_val(v) for v in lst[:10]]
            + ["..."]
            + [reduce_val(v) for v in lst[-10:]]
        )

    return [reduce_val(v) for v in lst]


def reduce_val(v):
    if np:
        if isinstance(v, (np.ndarray, np.matrix)):
            v = v.tolist()
    if isinstance(v, (list, tuple)):
        return reduce_list(v)
    if isinstance(v, dict):
        return {k: reduce_val(v) for k, v in v.items()}
    return v


def stringify_value(v):
    if isinstance(v, (list, tuple)):
        return ", ".join(stringify_value(vv) for vv in v)
    if isinstance(v, dict):
        try:
            return json.dumps(v, indent=2)
        except Exception:
            try:
                return json.dumps(
                    {str(k): stringify_value(vv) for k, vv in v.items()}, indent=2
                )
            except Exception:
                pass
    return str(v)


def repr_va(repr_va) -> Tuple[str, str]:
    if repr_va is None:
        return "null", "text/plain"

    if hasattr(repr_va, "_repr_html_"):
        return repr_va._repr_html_(), "text/html"
    elif hasattr(repr_va, "_repr_markdown_"):
        return repr_va._repr_markdown_(), "text/markdown"
    elif hasattr(repr_va, "_repr_svg_"):
        return repr_va._repr_svg_(), "image/svg+xml"
    elif hasattr(repr_va, "_repr_png_"):
        return repr_va._repr_png_(), "image/png"
    elif hasattr(repr_va, "_repr_jpeg_"):
        return repr_va._repr_jpeg_(), "image/jpeg"
    elif hasattr(repr_va, "_repr_json_"):
        return repr_va._repr_json_(), "application/json"
    elif hasattr(repr_va, "_repr_pretty_"):
        return repr_va._repr_pretty_(), "text/plain"
    else:
        return stringify_value(reduce_val(repr_va)), "text/plain"


class NodeIO(EventEmitterMixin, ObjectLoggerMixin, ABC):
    """Base class for all Node inputs and outputs."""

    def __init__(self, properties: IOProperties | dict | None = None, **kwargs):
        super().__init__()
        self._node: Node | None = None
        self._edges: List[Edge] = []
        if properties is None:
            properties = {}
        properties.update(kwargs)  # type: ignore
        self._properties: FixedIOProperties = self.set_default_properties(properties)

        self._type = IOType.get_type(self._properties["type"])
        self._properties["type"] = self._type.typestring

    # region Properties
    def set_default_properties(
        self, properties: IOProperties | dict
    ) -> FixedIOProperties:
        """Fill in default values for the properties to a given dictionary.

        Parameters
        ----------
        properties :
            IOProperties | dict: dictionary of properties

        Returns
        -------
        IOProperties:
            dictionary of properties with default values filled in

        """
        new_properties: FixedIOProperties = FixedIOProperties(
            id=properties.get("id", uuid.uuid4().hex[:8]),
            type=properties.get("type", "any"),
            required=properties.get("required"),
            default_value=properties.get("default_value"),
            allows_multiple=properties.get("allows_multiple", True),
            does_trigger=properties.get("does_trigger", True),
            trigger_on_get=properties.get("trigger_on_get", False),
            options=properties.get("options", None),
        )
        return new_properties

    @property
    def options(self) -> List[Tuple[str, Any]] | None:
        """Returns the options of this NodeIO.

        Returns
        -------
        List[Tuple[str, Any]]:
            options of this NodeIO
        """
        return self._properties.get("options")

    @options.setter
    def options(self, options: List[Tuple[str, Any]] | None) -> None:
        """Sets the options of this NodeIO.

        Parameters
        ----------
        options : List[Tuple[str, Any]]:
            options to set

        Returns
        -------
        None:

        """
        self._properties["options"] = options

    @property
    def properties(self) -> FixedIOProperties:
        """Returns a copy of the properties of this NodeIO.
        Returns
        -------
        IOProperties:
            copy of the properties of this NodeIO
        """
        return copy.deepcopy(self._properties)

    @property
    def id(self) -> NodeIOId:
        """Returns the id of this NodeIO.

        Returns
        -------
        str:
            id of this NodeIO

        """
        return self._properties["id"]

    @id.setter
    def id(self, new_id: str) -> None:
        """

        Parameters
        ----------
        new_id : str:
            new id for this NodeIO

        Returns
        -------
        None:
        Raises
        ------
        IOError:
            if the new id is already in use by another NodeIO in the same node

        """
        old_id = self.id
        if new_id == old_id:
            return
        self._properties["id"] = new_id
        if self.node is not None:
            if self.node.io.get(new_id) is not None:
                if self.node.io.get(new_id) != self:
                    raise NodeIOError(
                        f"NodeIO with id {new_id} already exists in node {self.node}"
                    )
                else:
                    self.node.change_io_id(old_id, new_id)

    @property
    def name(self) -> str:
        """Returns the name of this NodeIO.

        Returns
        -------
        str:
            name of this NodeIO
        """
        return self._properties.get("name", self.id)

    @property
    def state(self) -> NodeIOState:
        """Returns the state of this NodeIO.
        Returns
        -------
        NodeState:
            state of this NodeIO

        """
        return {"properties": self.properties}

    @property
    def node(self) -> Node | None:
        """Returns the node this NodeIO is connected to.

        Returns
        -------
        Node | None:
            node this NodeIO is connected to or None if it is not connected to a node
        """
        return self._node

    @node.setter
    def node(self, node: Node) -> None:
        """

        Parameters
        ----------
        node : Node:
            node to connect this NodeIO to


        Returns
        -------
        None:

        Raises
        ------
        IOError:
            if the node is already set
        IOError:
            if the node is not of type Node

        """
        from .node import Node  # pylint: disable=import-outside-toplevel

        if self._node is not None:
            raise NodeIOError("node is already set")
        if not isinstance(node, Node):
            raise NodeIOError(f"node must be of type Node, not {type(node)}")

        reset_cache(self, "is_ready")
        self._node = node

    @property
    def trigger_on_get(self) -> bool:
        """Returns whether this NodeIO triggers on get.

        Returns
        -------
        bool:
            whether this NodeIO triggers on get

        """
        return self._properties.get("trigger_on_get", False)

    @property
    def required(self) -> bool:
        """Returns whether this NodeIO is required.

        Returns
        -------
        bool:
            whether this NodeIO is required
        """
        return self._properties.get("required") or False

    @property
    def default_value(self) -> Any:
        """Returns the default value of this NodeIO.

        Returns
        -------
        Any:
            default value of this NodeIO
        """
        dval = self._properties.get("default_value")
        if dval is None:
            return None
        return self.to_type(dval)

    @property
    def ready(self) -> bool:
        """Returns whether this NodeIO is ready to be used.
        An NodeIO is ready if it is not required or if it is connected to a node and has a value.

        Returns
        -------
        bool:
            whether this NodeIO is ready to be used

        """
        return self.is_ready()[0]

    @cached_call("is_ready")
    def is_ready(self) -> Tuple[bool, str]:
        return True, ""

    @property
    def value(self) -> Any:
        """Getter and setter for the value of this NodeIO.
        Setting the value will  internally call the set_value method with mark_for_trigger=None.

        Raises
        ------
        NodeIOError:
            if the NodeIO is not connected to a node
        MissingValueError:
            if the NodeIO has no value

        """
        if self._node is None:
            raise NodeIOError(
                f"NodeIO {self.id} is not connected to a node, so it has no value"
            )
        _val: Any | None = self._node.get_data(self.id)
        if _val is not None:
            return _val

        defval: Any = self.default_value
        if defval is not None:
            return defval
        raise MissingValueError(f"NodeIO {self} has no value")

    @property
    def value_or_none(self):
        """Getter value of this NodeIO.
        Returns None if the NodeIO has no value.
        """
        try:
            return self.value
        except (MissingValueError, NodeIOError):
            return None

    @value.setter
    def value(self, value: Any):
        """setter"""
        self.set_value(value)

    @property
    def length(self) -> int:
        """Returns the number of edges connected to this NodeIO.

        Returns
        -------
        int:
            number of edges connected to this NodeIO
        """
        return len(self)

    def __str__(self) -> str:
        return f"{self.id}({self.node})"

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self) -> int:
        return len(self._edges)

    @property
    def does_trigger(self) -> bool:
        """Returns whether this NodeIO triggers the node it is connected to. when its value changes.
        Returns
        -------
        bool:
            whether this NodeIO triggers the node it is connected to
        """
        return self._properties.get("does_trigger", True)

    @property
    def allows_multiple(self) -> bool:
        """Property that indicates whether this NodeIO allows multiple edges.

        Returns
        -------
        bool:
            whether this NodeIO allows multiple edges
        """
        return self._properties.get("allows_multiple", True)

    @property
    def typestring(self) -> str:
        """Returns the typestring of this NodeIO.

        Returns
        -------
        str:
            typestring of this NodeIO
        """
        return self._type.typestring

    # endregion Properties

    # region Value
    def to_type(self, value: Any) -> Any:
        """Casts the given value to the type of this NodeIO.

        Parameters
        ----------
        value :
            Any: value to cast

        Returns
        -------
        Any:
            value casted to the type of this NodeIO

        """
        return self._type.cast_if_needed(value)

    @resets_cache("is_ready")
    def set_default_value(self, value: Any):
        """Sets the default value of this NodeIO.

        Parameters
        ----------
        value : Any:
            value to set as default value

        Returns
        -------


        """
        value = self.to_type(value)
        self._properties["default_value"] = value

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        raise NotImplementedError()

    def is_output(self):
        """Returns whether this NodeIO is an output.

        Returns
        -------
        bool:
            whether this NodeIO is an output

        """
        raise NotImplementedError()

    @resets_cache("is_ready")
    def set_value(
        self,
        value: Any,
        quiet: bool = False,
        update_only: bool = True,
    ) -> Tuple[Any, bool]:
        """Sets the value of this NodeIO.
        This will internally call the update_data method of the node and
        requets a trigger on the node if mark_for_trigger is True.

        Parameters
        ----------
        value : Any:
            value to set
        mark_for_trigger : bool:
            whether to mark the node for trigger
        update_only : bool:
            whether to only update the value if it has changed


        Raises
        ------
        IOError:
            if the NodeIO is not connected to a node

        """

        if self._node is None:
            raise NodeIOError("NodeIO is not connected to a node, so it has no value")
        if value is not None:
            try:
                value = self.to_type(value)
            except Exception as exc:  # pylint: disable=broad-except
                suberror = NodeIOError(
                    f"Could not set value of '{self.id}' to '{value}' because of '{exc}'"
                )
                if self.node:
                    return self.node.error(suberror), False

                raise suberror from exc

        self.logger.debug("Setting value to %s", value)
        oldvalue = self._node.get_data(self.id)
        if update_only:
            try:
                if self._type.equal(value, oldvalue):
                    return value, False
            except Exception:  # pylint: disable=broad-except
                # TODO: generalize comparison
                self.logger.warn("Cannot compare values")

        self._node._set_data(
            name=self.id,
            value=value,
            quiet=quiet,
        )
        if not quiet:
            self.emit(
                "value_changed",
                Message_NodeIO_ValueChanged(
                    old=oldvalue,
                    new=value,
                ),
            )
        return value, True

    @resets_cache("is_ready")
    def set_value_and_default(self, value: Any) -> Any:
        """Sets the value if this NodeIO and also sets the new value as default value.

        Parameters
        ----------
        value : Any:
            value to set

        Returns
        -------
        None:


        """
        value, _ = self.set_value(value)
        self.set_default_value(value)
        return value

    # endregion Value

    # region Edges

    def get_other_io(self) -> List[NodeIO]:
        """Returns all IOs connected to the current IO.

        Returns
        -------
        List[NodeIO]:
            list of IOs connected to the current IO
        """
        if self.length == 0:
            return []
        return [e.other_io(self) for e in self._edges]

    def get_other_nodes(self) -> List[Node]:
        """Returns all nodes connected to the current IO.

        Returns
        -------
        List[Node]:
            list of nodes connected to the current IO
        """
        nodes: List[Node] = []
        for other_io in self.get_other_io():
            if other_io.node is not None:
                nodes.append(other_io.node)
        return list(set(nodes))

    def connectable_to(self, other: NodeIO) -> bool:
        """Returns whether this NodeIO can be connected to the given NodeIO.

        Parameters
        ----------
        other : NodeIO:
            NodeIO to check against

        Returns
        -------
        bool:
            whether this NodeIO can be connected to the given NodeIO


        """
        return Edge.createable(self, other)

    @resets_cache("is_ready")
    def connect_to(self, other: NodeIO, replace_if_necessary: bool = False) -> Edge:
        """
        Connects this NodeIO to the given NodeIO.

        Parameters
        ----------
        other : NodeIO:
            NodeIO to connect to
        replace_if_necessary : bool:
            whether to replace the current edge if necessary

        Returns
        -------
        Edge:
            the created edge

        Raises
        ------
        TypeError:
            if other is not of type NodeIO
        IOError:
            if this NodeIO is not connected to a node
        IOError:
            if other is not connected to a node
        IOError:
            if the connection is not allowed
        IOError:
            if the NodeIO already has an edge and does not allow multiple edges

        """
        # make shure other is of type NodeIO
        if not isinstance(other, NodeIO):
            raise TypeError(f"other must be of type NodeIO, not {type(other)}")

        # make sure both nodes are connected to a node
        if self.node is None:
            raise NodeIOError("cannot connect NodeIO without node")
        if other.node is None:
            raise NodeIOError("cannot connect NodeIO without node")

        # node already connected to other node
        if other in self.get_other_io():
            return self.get_edge_to(other)

        # check if connection is allowed
        if not self.connectable_to(other):
            raise NodeIOError(
                f"cannot connect {self.id} to {other.id} in node {self.node}"
            )

        # check for self and other individually

        for _io in [self, other]:
            if _io.length > 0:
                if not _io.allows_multiple:
                    if replace_if_necessary:
                        _io.disconnect_from(_io.get_other_io()[0])
                    else:
                        raise NodeIOError(
                            f"multiple connections to {_io.id} are not allowed"
                        )

        # create edge
        new_edge = Edge(self, other)
        self._add_edge(new_edge)
        other._add_edge(new_edge)  # pylint: disable=protected-access

        # call event
        new_edge.start_node.emit(
            "new_connection",
            Message_Node_NewConnection(
                edge=new_edge,
            ),
        )

        self.emit("connected", Message_NodeIO_Connected(to=other))
        other.emit("connected", Message_NodeIO_Connected(to=self))
        reset_cache(self, "is_ready")
        reset_cache(other, "is_ready")

        return new_edge

    def c(self, *args, **kwargs) -> Edge:  # pylint: disable=invalid-name
        """Alias for connect_to."""
        return self.connect_to(*args, **kwargs)

    @resets_cache("is_ready")
    def _add_edge(self, edge: Edge):
        """Private method to add an edge to this NodeIO.

        Parameters
        ----------
        edge : Edge:
            edge to add

        """
        self._edges.append(edge)

    def is_connected(self) -> bool:
        """Returns whether this NodeIO is connected to another NodeIO.

        Returns
        -------
        bool:
            whether this NodeIO is connected to another NodeIO
        """
        return len(self) > 0

    @resets_cache("is_ready")
    def _remove_edge(self, edge: Edge) -> bool:
        """Private method to remove an edge from this NodeIO.

        Parameters
        ----------
        edge : Edge:
            edge to remove

        Returns
        -------
        bool:
            whether the edge was removed
        """
        if edge not in self._edges:
            return False
        self._edges.remove(edge)
        return True

    def get_edge_to(self, other: NodeIO) -> Edge:
        """Returns the edge to the given NodeIO.

        Parameters
        ----------
        other : NodeIO:
            NodeIO to get the edge to

        Returns
        -------
        Edge:
            the edge to the given NodeIO

        Raises
        ------
        IOError:
            if no edge to the given NodeIO exists

        """
        for edge in self._edges:
            if edge.other_io(self) == other:
                return edge
        raise NodeIOError(f"no edge to {other.id} exists")

    def get_edges(self) -> List[Edge]:
        """Returns all edges connected to this NodeIO.

        Returns
        -------
        List[Edge]:
            all edges connected to this NodeIO
        """
        return [edge for edge in self._edges]

    def disconnect_from(self, other: NodeIO):
        """Disconnects this NodeIO from the given NodeIO.

        Parameters
        ----------
        other : NodeIO:
            NodeIO to disconnect from

        Raises
        ------
        IOError:
            if no edge to the given NodeIO exists

        """
        edge: Edge = self.get_edge_to(other)
        rem1 = self._remove_edge(edge)
        rem2 = other._remove_edge(edge)  # pylint: disable=protected-access
        if rem1 or rem2:
            self.emit("disconnected", Message_NodeIO_Disconnected(other=other))
            other.emit("disconnected", Message_NodeIO_Disconnected(other=self))
            if edge.start.node:
                edge.start.node.emit(
                    "edge_removed", Message_Node_Disconnected(edge=edge)
                )

    # endregion Edges

    def serialize(self) -> IOProperties:
        """Generates a JSON serializable dictionary of the NodeIO.

        Returns
        -------
        IOProperties:
            JSON serializable dictionary of the NodeIO
        """
        full_properties = cast(IOProperties, self.properties)
        default_properties = self.set_default_properties({})

        deep_remove_dict_on_equal(full_properties, default_properties)  # type: ignore
        return full_properties

    def full_serialize(self) -> FullNodeIOJSON:
        """Generates a JSON serializable dictionary of the NodeIO.

        Returns
        -------
        FullNodeIOJSON:
            JSON serializable dictionary of the NodeIO
        """
        return {
            "id": self.id,
            "type": self.typestring,
            "name": self.name,
            "is_input": self.is_input(),
            "connected": self.is_connected(),
            "node": self._node.id if self._node else None,
            "value": self.value_or_none,
            "does_trigger": self.does_trigger,
            "options": self.options,
        }

    def _repr_json_(self):
        rep: dict = self.full_serialize()  # type: ignore
        v = repr_va(rep["value"])
        rep["value"] = {"value": v[0], "mime": v[1]}
        return rep

    @resets_cache("is_ready")
    def remove(self):
        """Removes the NodeIO from the node.
        First disconnects all edges, then removes the NodeIO from the node.
        """

        for nio in self.get_other_io():
            self.disconnect_from(nio)

        try:
            if self.node is not None:
                self.node.remove_io(self)
        except NodeError:
            # this is excpected to happen since node remove also calls NodeIO.remove
            pass
        for edg in self.get_edges():
            edg.remove()

        self._edges = []
        self._node = None
        self.emit("removed")

    @abstractmethod
    def mark_for_trigger(self, src: str | None = None, trigger: bool = False):
        """Requests a trigger for the node of this NodeIO or other Nodes connected to it.

        Parameters
        ----------
        src : str:
            source of the trigger (Default value = None)

        Raises
        ------
        IOError:
            if the NodeIO is not connected to a node

        """
        raise NotImplementedError()


GenericNodeIO = TypeVar("GenericNodeIO", bound=NodeIO)  # pylint: disable=invalid-name


class NodeInput(NodeIO):
    """NodeInput subclass of NodeIO."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on("connected", self.on_connect_sig)
        self.on("disconnected", self.on_disconnect_sig)

    def on_disconnect_sig(self, **kwargs):
        """Slot for the disconnected signal.

        Parameters
        ----------
        msg : Message_NodeIO_Disconnected:
            message of the signal
        """
        self.value = None

    def is_grabbing_input(self) -> bool:
        """Returns whether this NodeInput is grabbing.

        Returns
        -------
        bool:
            whether this NodeInput is grabbing an input
        """
        return any([edge.is_grabbing() for edge in self._edges])

    def disconnect_from(self, other: NodeIO):
        super().disconnect_from(other)
        self.value = self.default_value

    @cached_call("is_ready")
    def is_ready(self) -> Tuple[bool, str]:
        s_ir = super().is_ready()
        if not s_ir[0]:
            return s_ir

        if self.required:
            if self.default_value is not None:
                return True, ""
            if self.is_grabbing_input():
                output = self.get_other_io()[0]
                if output.node is None:
                    return False, "no node on grabbing input"
                if output.node.has_grabbing_input():
                    if not output.node.operable:
                        return False, "node to grab from not operable"
                else:
                    if output.value_or_none is None:
                        return False, "no grabbable value"
                return True, ""
            if self.value_or_none is None:
                return False, "required, but no value"
            # if self.value_or_none is None:
            #    if len(self._edges) == 0:
            #        return False, "required, but no value and no edges"
            # else:
            #     if self.grab_value() is None:
            #         return False, "required, but no value"
        return s_ir

    def on_connect_sig(self, to: NodeIO, **kwargs):
        """Event handler for the connected event.

        Parameters
        ----------
        msg : Message_NodeIO_Connected:
            message object
        """
        edge = self.get_edge_to(to)
        if edge.end == self:
            self.update_value()
        self.trigger("connected")

    @resets_cache("is_ready")
    def set_default_properties(
        self, properties: IOProperties | dict
    ) -> FixedIOProperties:
        """Sets the default properties of the NodeInput."""
        properties.setdefault("allows_multiple", False)
        properties.setdefault("does_trigger", True)
        properties.setdefault("required", True)
        return super().set_default_properties(properties)

    @resets_cache("is_ready")
    def update_value(
        self, new_value: Any = None, mark_for_trigger: bool | None = None
    ) -> Any:
        """Updates the value of the NodeInput.
        If new_value is None, the value of the connected NodeOutput is used.

        Parameters
        ----------
        new_value : Any:
            new value to set (Default value = None)
        mark_for_trigger : bool:
            whether to mark the node for trigger (Default value = None)


        Returns
        -------
        """
        if new_value is None:
            for edge in self._edges:
                new_value = edge.other_io(self).value_or_none
                if new_value is not None:
                    break

        if new_value is not None:
            return self.set_value(new_value, mark_for_trigger=mark_for_trigger)[0]
        return None

    def mark_for_trigger(self, src: str | None = None, trigger: bool = False):
        """Requests a trigger for the node of this NodeInput.

        Parameters
        ----------
        src : str:
            source of the trigger (Default value = None)

        Raises
        ------
        IOError:
            if the NodeInput is not connected to a node

        """
        if self.node is None:
            raise NodeIOError("cannot trigger NodeInput without node")
        if trigger:
            self.node.request_trigger_and_trigger(src)
        else:
            self.node.request_trigger(src)

    def trigger(
        self, src: str | None = None, trigger_queue: TriggerQueue | None = None
    ) -> TriggerQueue | None:
        """Triggers the node of this NodeInput.

        Parameters
        ----------
        src : str:
            source of the trigger (Default value = None)

        Raises
        ------
        IOError:
            if the NodeInput is not connected to a node

        """
        if self.node is None:
            raise NodeIOError("cannot trigger NodeInput without node")
        if src is None:
            src = f"trigger {self.id}"
        return self.node.request_trigger_and_trigger(
            src=src, trigger_queue=trigger_queue
        )

    @resets_cache("is_ready")
    def set_value(
        self,
        value: Any,
        quiet: bool = False,
        mark_for_trigger: bool | None = None,
        update_only: bool = True,
    ) -> tuple[Any, bool]:
        value, new = super().set_value(
            value=value,
            quiet=quiet,
            update_only=update_only,
        )

        if mark_for_trigger is None:
            mark_for_trigger = self.does_trigger
        if mark_for_trigger and new:
            self.mark_for_trigger(f"value_set {self.id}")
        return value, new

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        return True

    def is_output(self):
        """Returns whether this NodeIO is an output.

        Returns
        -------
        bool:
            whether this NodeIO is an output

        """
        return False


class NodeOutput(NodeIO):
    """NodeOutput subclass of NodeIO."""

    @resets_cache("is_ready")
    def set_default_properties(
        self, properties: IOProperties | dict
    ) -> FixedIOProperties:
        """Sets the default properties of the NodeInput."""
        properties.setdefault("allows_multiple", True)
        properties.setdefault("does_trigger", False)
        properties.setdefault("trigger_on_get", False)
        return super().set_default_properties(properties)

    def mark_for_trigger(self, src: str | None = None, trigger: bool = False):
        """Requests a trigger for all nodes connected to this NodeOutput.

        Parameters
        ----------
        src : str:
            source of the trigger (Default value = None)

        """
        if self.node is None:
            return

        for edge in self.get_edges():
            if edge.is_grabbing():
                continue
            edge.other_io(self).mark_for_trigger(src, trigger=trigger)

    def trigger(
        self, src: str | None = None, trigger_queue: TriggerQueue | None = None
    ) -> List[TriggerQueue | None]:
        """Triggers the connected Nodes of this NodeOutput.

        Parameters
        ----------
        src : str:
            source of the trigger (Default value = None)

        Raises
        ------
        IOError:
            if the NodeOutput is not connected to a node

        """
        if self.node is None:
            raise NodeIOError("cannot trigger NodeInput without node")
        self.mark_for_trigger(src=self.id)
        return [
            edge.end_node.trigger_if_requested(trigger_queue=trigger_queue)
            for edge in self.get_edges()
            if edge.start == self
        ]

    @resets_cache("is_ready")
    def set_value(
        self,
        value: Any,
        quiet: bool = False,
        mark_for_trigger: bool | None = None,
        update_only: bool = True,
    ) -> tuple[Any, bool]:
        value, new = super().set_value(
            value=value, quiet=quiet, update_only=update_only
        )

        self.push(mark_for_trigger=mark_for_trigger)

        return value, new

    def push(
        self,
        mark_for_trigger: bool | None = None,
    ):
        """Pushes the value of this NodeOutput to all connected NodeInputs."""
        for edge in self.get_edges():
            other_io = edge.other_io(self)
            if not isinstance(other_io, NodeInput):
                continue
            if edge.is_grabbing():
                other_io.update_value(mark_for_trigger=False)
                reset_cache(other_io, "is_ready")
            else:
                other_io.update_value(mark_for_trigger=mark_for_trigger)

    def is_input(self):
        """Returns whether this NodeIO is an input.

        Returns
        -------
        bool:
            whether this NodeIO is an input

        """
        return False

    def is_output(self):
        """Returns whether this NodeIO is an output.

        Returns
        -------
        bool:
            whether this NodeIO is an output

        """
        return True

    def set_default_value(self, *args, **kwargs):
        """quietly ignores the default value for NodeOutputs"""
        return


class Edge:
    """Edge class to connect two NodeIOs."""

    @staticmethod
    def createable(start: NodeIO, end: NodeIO) -> bool:
        """Returns whether an Edge can be created between start and end.

        Parameters
        ----------
        start : NodeIO:
            start NodeIO
        end : NodeIO:
            end NodeIO

        Returns
        -------
        bool:
            whether an Edge can be created between start and end

        """
        if start == end:
            return False
        if start.node == end.node:
            return False
        if isinstance(start, NodeInput) and isinstance(end, NodeInput):
            return False
        if isinstance(start, NodeOutput) and isinstance(end, NodeOutput):
            return False
        return True

    def __init__(self, start: NodeIO, end: NodeIO):
        super().__init__()
        if start == end:
            raise EdgeError("cannot connect to self")
        if start.node == end.node:
            raise EdgeError("cannot connect to same node")
        if isinstance(self, NodeInput) and isinstance(end, NodeInput):
            raise EdgeError("cannot connect input to input")
        if isinstance(self, NodeOutput) and isinstance(end, NodeOutput):
            raise EdgeError("cannot connect output to output")
        self._start = start
        self._end = end

    def is_grabbing(self) -> bool:
        """Returns whether this Edge is grabbing.

        Returns
        -------
        bool:
            whether this Edge is grabbing

        """
        return isinstance(self._start, NodeInput)

    def other_node(self, node: Node) -> Node:
        """Returns the other Node of this Edge.

        Parameters
        ----------
        node : Node:
            Node to get the other Node from

        Returns
        -------
        Node:
            the other Node of this Edge

        Raises
        ------
        EdgeError:
            if node is not in this Edge

        """
        if node == self.start_node:
            return self.end_node
        if node == self.end_node:
            return self.start_node
        raise EdgeError("node not in edge")

    def other_io(self, node_io: NodeInput | NodeOutput | NodeIO) -> NodeIO:
        """Returns the other NodeIO of this Edge.

        Parameters
        ----------
        node_io : NodeIO:
            NodeIO to get the other NodeIO from

        Returns
        -------
        NodeIO:
            the other NodeIO of this Edge

        Raises
        ------
        EdgeError:
            if io is not in this Edge

        """
        if node_io == self._start:
            return self._end
        if node_io == self._end:
            return self._start

        raise EdgeError("io not in edge")

    def disconnect(self):
        """Disconnects this Edge."""
        self._start.disconnect_from(self._end)

    def remove(self):
        """Alias for disconnect."""
        self.disconnect()

    @property
    def start(self) -> NodeIO:
        """Returns the start NodeIO of this Edge."""
        return self._start

    @property
    def end(self) -> NodeIO:
        """Returns the end NodeIO of this Edge."""
        return self._end

    @property
    def start_node(self) -> Node:
        """Returns the start Node of this Edge."""
        if self._start.node is None:
            raise EdgeError("start node is None")
        return self._start.node

    @property
    def end_node(self) -> Node:
        """Returns the end Node of this Edge."""
        if self._end.node is None:
            raise EdgeError("end node is None")
        return self._end.node

    @property
    def id(self) -> str:
        """Returns the id of this Edge."""
        if self.start.node is None or self.end.node is None:
            raise EdgeError("cannot get id of edge without nodes")
        return f"{self.start.node.id}_{self.start.id}_{self.end.node.id}_{self.end.id}"

    def full_serialize(self) -> FullEdgeJSON:
        return {
            "start_id": self._start.node.id if self._start.node is not None else None,
            "start_io": self._start.id,
            "end_id": self._end.node.id if self._end.node is not None else None,
            "end_io": self._end.id,
        }

    def _repr_json_(self):
        return self.full_serialize()


class EdgeSerializationInterface(NamedTuple):
    """Edge serialization interface."""

    start_id: int | NodeIdType
    start_io: NodeIOId
    end_id: int | NodeIdType
    end_io: NodeIOId


class FullEdgeJSON(TypedDict):
    """Full JSON representation of an Edge."""

    start_id: str | None
    start_io: str
    end_id: str | None
    end_io: str


class FullNodeIOJSON(TypedDict):
    """Full JSON representation of a NodeIO."""

    id: str
    name: str
    type: str
    is_input: bool
    connected: bool
    node: str | None
    value: Any
    does_trigger: bool
    options: List[Tuple[str:any]] | None
