"""
module for base Node class
"""
from __future__ import annotations
import copy
import json
import uuid
import inspect
import asyncio
from time import perf_counter as _deltatimer
from abc import ABCMeta, abstractmethod
from typing import (
    List,
    Set,
    Dict,
    Type,
    Tuple,
    Any,
    TYPE_CHECKING,
)
from typing_extensions import TypedDict, Self

from .errors import (
    NodeStructureError,
    NodeInitalizationError,
    NodeIOError,
    NodeError,
    NodeSpaceError,
    NotOperableException,
    DisabledException,
    TriggerException,
)

from .io import (
    NodeInput,
    NodeOutput,
    NodeIO,
    Edge,
    GenericNodeIO,
    FullNodeIOJSON,
)

from ._typing import (
    NodeStatus,
    NodeIdType,
    NodeDataName,
    NodeIOId,
    Message_Node_SetData,
    PropIODict,
    NodeStateInterface,
    Message_Node_SetNodeSpace,
    Message_Node_AddIO,
    Message_Node_AddInput,
    Message_Node_AddOutput,
    Message_Node_RemoveIO,
    Message_Node_CheckStatus,
)
from .mixins import (
    EventEmitterMixin,
    EventCallback,
    ObjectLoggerMixin,
    ProxyableMixin,
)
from .utils import (
    deep_fill_dict,
    deep_remove_dict_on_equal,
)


if TYPE_CHECKING:
    from .nodespace import NodeSpace

# region global settings

NODE_MAX_NAME_LENGTH = 20

# endregion global settings

NodeDataDict = Dict[NodeDataName, Any]


class TriggerTask:
    def __init__(self, task: asyncio.Task):
        self._trigger_queue: TriggerQueue | None = None
        self._task = task

    @property
    def trigger_queue(self):
        return self._trigger_queue

    @trigger_queue.setter
    def trigger_queue(self, value):
        if self._trigger_queue is not None:
            raise RuntimeError("trigger_queue can only be set once")
        self._trigger_queue = value

    def __await__(self):
        return self._task.__await__()

    def done(self):
        return self._task.done()

    def cancel(self):
        return self._task.cancel()

    def exception(self):
        return self._task.exception()


class TriggerQueue:
    def __init__(self):
        self._tasks: List[TriggerTask] = []
        # self.id = uuid.uuid4().int

    @property
    def is_done(self):
        return not self._tasks

    def append(self, task: TriggerTask):
        task._trigger_queue = self
        self._tasks.append(task)

    async def await_done(self):
        while not self.is_done:
            task = self._tasks.pop(0)
            await task

    def __await__(self):
        return self.await_done().__await__()


class NodeProperties(TypedDict, total=False):
    """TypedDict for Node properties"""

    id: NodeIdType
    name: str
    io: PropIODict
    disabled: bool
    requirements: List[dict]
    trigger_on_create: bool


class NodeSerializationInterface(NodeProperties, total=False):
    """TypedDict for Node serialization"""

    nid: str


class FullNodeClassJSON(TypedDict):
    name: str
    node_id: str
    trigger_on_create: bool


class FullNodeJSON(TypedDict):
    name: str
    id: str
    node_id: str
    disabled: bool
    io: Dict[str, FullNodeIOJSON]
    data: NodeDataDict
    status: NodeStatus
    requirements: List[dict]


# region helpers
class NodeMetaClass(ABCMeta):
    """Metaclass for Node class"""

    NODECLASSES: Dict[str, Type[Node]] = {}

    def __new__(  # pylint: disable=bad-mcs-classmethod-argument
        mcls,  # type: ignore
        name,
        bases,
        namespace,
        /,
        **kwargs,
    ):
        new_cls: Type[Node] = super().__new__(
            mcls, name, bases, namespace, **kwargs  # type: ignore
        )
        if new_cls.node_id is None:
            raise NodeStructureError(
                f"Node class '{new_cls.__name__}' does not have a node_id"
            )
        if new_cls.node_id in NodeMetaClass.NODECLASSES:
            raise NodeStructureError(
                f"Node class '{new_cls.__name__}'(module={new_cls.__module__})"
                f" has the same node_id as '{NodeMetaClass.NODECLASSES[new_cls.node_id].__name__}"
                f"(module={NodeMetaClass.NODECLASSES[new_cls.node_id].__module__}):"
                f" '{new_cls.node_id}' "
            )
        NodeMetaClass.NODECLASSES[new_cls.node_id] = new_cls
        return new_cls


# requires initialization for Node methods which check if the node is initialized
def requires_init(func):
    """Decorator for Node methods which require the node to be initialized"""

    def requires_init_wrapper(self: Node, *args, **kwargs):
        if not self.initialized:
            raise NodeInitalizationError(f"Node '{self.name}' is not initialized")
        return func(self, *args, **kwargs)

    return requires_init_wrapper


class NodeIODict(Dict[str, NodeIO]):
    """Dict for NodeIO objects"""

    def __setitem__(self, key: str, value: NodeIO):
        if not isinstance(value, NodeIO):
            raise NodeStructureError(
                f"only NodeIO objects can be added to NodeIODict,"
                f" not '{type(value)}'"
            )
        return super().__setitem__(key, value)

    def __setattr__(self, __name: str, __value: NodeIO) -> None:
        return self.__setitem__(__name, __value)

    def __getattr__(self, __name: str) -> NodeIO:
        return self.__getitem__(__name)

    def __call__(self, io_name) -> NodeIO:
        """call the nodeio dict entry via node.io(...) handles different shortcut.
        It sould not be used  under production since its not long term save.
        Returns:
            NodeIO: the NodeIO object

        """
        io = self[io_name]
        return io


# endregion helpers

# type ([^=]*)=([^;]*); "$1":Literal[$2],


class Node(
    EventEmitterMixin, ObjectLoggerMixin, ProxyableMixin, metaclass=NodeMetaClass
):
    """Base class for all nodes

    Attributes:
        node_id (str): unique id for the node class
        trigger_on_create (bool): if True, the node will trigger on creation
        pure (bool): if True, the node function is pure and only
        depends on the inputs not on some external state, like URL response
    """

    node_id: str = "basenode"
    PURE = True
    trigger_on_create: bool = True
    requirements: List[dict] = []

    def __init__(
        self,
        properties: NodeProperties | Dict[str, Any] | None = None,
        default_listener: Dict[str, List[EventCallback]] = {},
        **kwargs,
    ):
        super().__init__()
        self.min_trigger_interval = 5
        self._in_trigger: bool = False
        self._triggertask: TriggerTask | None = None
        self._initialized: bool = False
        self._request_trigger = False
        self._last_trigger_time: float = 0
        self._triggerdelay: int = 0
        self._nodespace: NodeSpace | None = None

        self._io: NodeIODict = NodeIODict()
        self._inputs: List[NodeInput] = []
        self._outputs: List[NodeOutput] = []
        self._data: Dict[NodeDataName, Any] = {}

        if properties is None:
            properties = {}
        for key, val in kwargs.items():
            properties[key] = val

        self._properties: NodeProperties = self.set_default_properties(properties)
        self._make_io()
        for event, listeners in default_listener.items():
            for listener in listeners:
                self.on(event, listener)

    def _make_io(self):
        indict = {}
        outdict = {}
        for key in dir(self):
            try:
                value = getattr(self, key)
                if isinstance(value, NodeIO):
                    if isinstance(value, NodeInput):
                        indict[key] = value.properties
                        indict[key]["id"] = key

                    elif isinstance(value, NodeOutput):
                        outdict[key] = value.properties
                        outdict[key]["id"] = key
                    else:
                        raise NodeStructureError(
                            f"NodeIO '{key}' of node '{self.name}' has an invalid type"
                        )
            except AttributeError:
                pass

        ios = {"ip": indict, "op": outdict}
        # check for backwardscompatibility where the
        # ios in to properties where not seperated in ip and op
        if "io" in self._properties:
            if "ip" not in self._properties["io"]:
                self._properties["io"]["ip"] = {}
            if "op" not in self._properties["io"]:
                self._properties["io"]["op"] = {}

            for key in list(self._properties["io"].keys()):
                if key != "ip" and key != "op":
                    if key in ios["ip"]:
                        self._properties["io"]["ip"][key] = self._properties["io"][key]
                        del self._properties["io"][key]
                    elif key in ios["op"]:
                        self._properties["io"]["op"][key] = self._properties["io"][key]
                        del self._properties["io"][key]

        deep_fill_dict(self._properties, {"io": ios})  # type: ignore
        # io is always present due to deepfill
        for key, value in self._properties["io"]["ip"].items():  # type: ignore
            if "id" not in value:
                value["id"] = key
            self.add_input(NodeInput(value))

        for key, value in self._properties["io"]["op"].items():  # type: ignore
            if "id" not in value:
                value["id"] = key
            self.add_output(NodeOutput(value))

    def initialize(self) -> Self:
        """
        Initialize the node.
        This method is called by the NodeSpace when the node is added to it.
        Returns the node.
        -------
        Node: self
        """
        if self._initialized:
            raise NodeInitalizationError(f"Node '{self.name}' is already initialized")
        self._initialized = True
        self.check_status()
        if self.operable and self.initial_trigger:
            self.request_trigger("trigger_on_create")

        if not self.disabled:
            self.enable()
        return self

    def enable(self) -> Self:
        """
        Enable the node.
        Returns
        -------
        Node: self

        """
        self.logger.info("enable")
        self.disabled = False
        if self.has_trigger_request:
            self.trigger()
        return self

    def remove(self):
        """Remove the node from the nodespace and clear all references.
        Then delete the node."""
        try:
            if self._nodespace is not None:
                self._nodespace.remove_node(self)
                return
        except NodeSpaceError:
            # this is excpected to happen since NodeSpace.remove_node calls Node.remove
            pass
        for node_input in [ip for ip in self._inputs]:
            self.remove_input(node_input)

        for node_output in [op for op in self._outputs]:
            self.remove_output(node_output)

        for nio in list(self._io.values()):
            self._remove_io(nio)
        self.emit("remove")

    # region Properties

    def set_default_properties(
        self, properties: Dict[str, Any] | NodeProperties
    ) -> NodeProperties:
        """Set default properties for the node. This method is called by the constructor.
        Parameters
        ----------
        properties: Dict[str, Any] | NodeProperties
            The target container for the properties
        Returns
        -------
        NodeProperties: The updated properties
        """
        out_properties = NodeProperties(
            id=properties.get("id", uuid.uuid4().hex),
            name=properties.get("name", self.__class__.__name__),
            disabled=properties.get("disabled", False),
            io=properties.get("io", {}),
            trigger_on_create=properties.get(
                "trigger_on_create", self.trigger_on_create
            ),
        )
        return out_properties

    @property
    def initial_trigger(self) -> bool:
        """Getter for the node initial trigger state.
        Returns
        -------
        bool: The node initial trigger state
        """
        return self._properties.get("trigger_on_create", self.trigger_on_create)

    @property
    def id(self) -> NodeIdType:
        """Getter for the node id
        Returns
        -------
        str: The node id

        """
        return self._properties["id"]  # type: ignore since id is always present

    @property
    def name(self) -> str:
        """Getter and setter for the node name.
        If the name is empty, the class name is used.
        If the name is longer than the maximum length, it is truncated.

        Parameters
        ----------
        value: str
            The new name

        Returns
        -------
        str: The node name

        """

        return self._properties.get("name", self.__class__.__name__)

    @name.setter
    def name(self, value: str):
        """Setter for the node name."""
        # assert string and strip
        value = str(value).strip()
        # assert length
        value = value[: self.max_name_length].strip()

        # assert not empty
        if value == "":
            value = self.__class__.__name__
        self._properties["name"] = value

    def change_name(self, name: str) -> str:
        """Change the name of the node.
        Parameters
        ----------
        name: str
            The new name
        Returns
        -------
        str: The new name
        """
        self.name = name
        return self.name

    def __str__(self) -> str:
        return f"{self.name}({self.id})"

    def __repr__(self) -> str:
        repstr = self.__str__() + ": "
        repstr += ", ".join([f"{ip.id}" for ip in self._inputs])
        repstr += " --> "
        repstr += ", ".join([f"{ip.id}" for ip in self._outputs])
        return repstr

    @property
    def max_name_length(self) -> int:
        """Maximum length of the node name"""
        return NODE_MAX_NAME_LENGTH

    @property
    def properties(self) -> NodeProperties:
        """Getter for the node properties
        Returns
        -------
        NodeProperties: Copy of the node properties (JSON serializable)
        """
        try:
            return json.loads(json.dumps(self._properties))
        except TypeError as err:
            raise TypeError(
                "cannot serialize node properties:" + str(self._properties)
            ) from err

    @property
    def disabled(self) -> bool:
        """Getter and setter for the node disabled state.
        Parameters
        ----------
        value: bool
            The new disabled state
        Returns
        -------
        bool: The node disabled state
        """
        return self._properties.get("disabled", False)

    @disabled.setter
    def disabled(self, value: bool):
        """Setter for the node disabled state."""
        self._properties["disabled"] = value

    @property
    def enabled(self) -> bool:
        """Getter for the node enabled state.
        Returns
        -------
        bool: The node enabled state
        """
        return not self.disabled

    def disable(self) -> Self:
        """Disable the node.
        Returns
        -------
        Node: self
        """

        self.logger.info("disable")
        self.disabled = True
        return self

    @property
    def initialized(self) -> bool:
        """Getter for the node initialized state.
        Returns
        -------
        bool: The node initialized state
        """
        return self._initialized

    @property
    def io(self) -> NodeIODict:
        """Getter for the node ios.
        Returns
        -------
        NodeIODict: The node ios
        """
        return self._io

    @property
    def operable(self) -> bool:
        """Getter for the node operable state.
        Returns
        -------
        bool: The node operable state
        """
        return self.is_operable()[0]

    @property
    def ready(self) -> bool:
        """Getter for the node ready state.
        Returns
        -------
        bool: The node ready state
        """
        return self.operable and not self.disabled

    @property
    def is_working(self) -> bool:
        """Getter for the node working state.
        Returns
        -------
        bool: The node working state
        """
        self._handle_trigger_task()

        if self._in_trigger or self._triggertask is not None:
            return True

        return False

    @property
    def nodespace(self) -> NodeSpace | None:
        """Getter and Setter for the node's nodespace.
        Parameters
        ----------
        nodespace: NodeSpace
            The new nodespace

        Returns
        -------
        NodeSpace: The node nodespace or None if the node is not added to a nodespace

        Raises
        -------
        NodeError: If the node is already added to a nodespace

        """
        return self._nodespace

    @nodespace.setter
    def nodespace(self, nodespace: NodeSpace):
        if self._nodespace == nodespace:
            return
        if self._nodespace is not None:
            raise NodeError("Node is already added to a nodespace")
        self._nodespace = nodespace
        self.emit("set.nodespace", Message_Node_SetNodeSpace(nodespace=nodespace))

    @property
    def has_trigger_request(self) -> bool:
        """Getter for the node trigger request state.
        Returns
        -------
        bool: The node trigger request state
        """

        return self._request_trigger

    @property
    def triggerdelay(self) -> float:
        """Getter and setter for the trigger delay in ms.
        Parameters
        ----------
        value: float
            The new trigger delay

        Returns
        -------
        float: The trigger delay
        """
        return self._triggerdelay

    @triggerdelay.setter
    def triggerdelay(self, value: int):
        """Setter for the trigger delay."""
        value = int(value)
        self._triggerdelay = value

    # endregion Properties

    # region IO

    def get_input_or_output(self, io_id: NodeIOId) -> NodeIO | None:
        """Get an node_input or node_output by id.
        Parameters
        ----------
        id: NodeIOId
            The id of the node_input or node_output
        Returns
        -------
        NodeIO | None: The node_input or node_output or None if not found
        """
        return self._io.get(io_id, None)

    def change_io_id(self, old_id: NodeIOId, new_id: NodeIOId):
        """Change the io_id of an node_input or node_output.
        Parameters
        ----------
        old_id: NodeIOId
            The old io_id of the node_input or node_output
        new_id: NodeIOId
            The new io_id of the node_input or node_output

        Raises
        ------
        NodeError: If the old io_id is not found or the new io_id is already in use
        """

        if self.get_input_or_output(old_id) is None:
            raise NodeError(f"{old_id} not found in io")

        if self.get_input_or_output(new_id) is not None:
            raise NodeError(f"{new_id} already in io")

        self._io[new_id] = self._io[old_id]
        self._io[new_id].id = new_id
        self._data[new_id] = self._data[old_id]
        del self._data[old_id]
        del self._io[old_id]

    def _add_io(self, io: GenericNodeIO) -> GenericNodeIO:
        """Add an node_input or node_output to the node.
        The io_id of the io is checked and if it is already in use, a number is added to the end.

        Parameters
        ----------
        io: GenericNodeIO
            The node_input or node_output to add
        Returns
        -------
        GenericNodeIO: The added node_input or node_output
        Raises
        ------
        IOError: If the io is not of type NodeIO or is already in the node
        """

        if not isinstance(io, NodeIO):
            raise NodeIOError(
                f"only NodeIO objects can be added to Nodes, not '{type(io)}'"
            )

        # if the io is already in the node, return it
        if io in self._io.values():
            raise NodeIOError(f"IO '{io.id}' is already in node '{self.name}'")

        # check if the io_id is already taken, if so, add a number to the end
        base_id = io.id
        if base_id in self._io:
            k = 1
            while f"{base_id}{k}" in self._io:
                k += 1
            io.id = f"{base_id}{k}"

        self._io[io.id] = io
        io.node = self

        self.logger.debug("adding io %s", io.id)

        # if self.<io.id> is not set or of NodeIO type, set it to the new io
        # this overwrites the default value of the io

        if getattr(self, io.id, None) is None or isinstance(
            getattr(self, io.id, None), NodeIO
        ):
            if isinstance(getattr(self, io.id, None), NodeIO):
                if getattr(self, "__default_io_" + io.id, None) is None:
                    setattr(self, "__default_io_" + io.id, getattr(self, io.id))
                else:
                    raise NodeIOError(
                        f"DefaultNodeIO '__default_io_{io.id}'"
                        f" is already set for node '{self.name}'"
                    )

            setattr(self, io.id, io)

        self._data[io.id] = io.value_or_none

        self.emit("add_io", Message_Node_AddIO(io=io))
        return io

    def add_input(self, node_input: NodeInput) -> NodeInput:
        """Add an node_input to the node.

        Parameters
        ----------
        node_input: NodeInput
            The node_input to add

        Returns
        -------
        NodeInput: The added node_input

        Raises
        ------
        IOError: If the node_input is not of type NodeInput or is already in the node

        """
        self.logger.debug("adding input %s", node_input)
        # assert node_input is NodeInput
        if not isinstance(node_input, NodeInput):
            raise NodeIOError(
                f"only NodeInput objects can be added to Nodes as node_input,"
                f" not '{type(node_input)}'"
            )

        # if the node_input is already in the node, return it
        if node_input in self._inputs:
            return node_input

        self._inputs.append(node_input)
        node_input = self._add_io(node_input)
        if node_input.default_value is not None:
            node_input.set_value(
                node_input.default_value, quiet=True, mark_for_trigger=False
            )

        self.emit("add_input", Message_Node_AddInput(node_input=node_input))

        return node_input

    def add_output(self, node_output: NodeOutput) -> NodeOutput:
        """Add an node_output to the node.

        Parameters
        ----------
        node_output: NodeOutput
            The node_output to add

        Returns
        -------
        NodeOutput: The added node_output

        Raises
        ------
        IOError: If the node_output is not of type NodeOutput or is already in the node
        """

        self.logger.debug("adding output %s", node_output)

        # assert node_output is NodeOutput
        if not isinstance(node_output, NodeOutput):
            raise NodeIOError(
                f"only NodeOutput objects can be added to Nodes as node_output,"
                f" not '{type(node_output)}'"
            )

        # if the node_output is already in the node, return it
        if node_output in self._outputs:
            return node_output

        self._outputs.append(node_output)
        node_output = self._add_io(node_output)
        if node_output.default_value is not None:
            node_output.set_value(node_output.default_value, True, False)

        self.emit("add_output", Message_Node_AddOutput(node_output=node_output))
        return node_output

    def push_output(self, node_output: NodeOutput, mark_for_trigger: bool = True):
        """Push the data of an node_output to the connected node_inputs.

        Parameters
        ----------
        node_output: NodeOutput
            The node_output to push
        mark_for_trigger: bool
            If True, the connected node_inputs will be marked for trigger

        Raises
        ------
        NodeError: If the node_output is not in the node

        """
        node_output.push(mark_for_trigger)

    def push_all_outputs(self, mark_for_trigger: bool = True):
        """Push the data of all node_outputs to the connected node_inputs.

        Parameters
        ----------
        mark_for_trigger: bool
            If True, the connected node_inputs will be marked for trigger

        """
        for node_output in self._outputs:
            node_output.push(mark_for_trigger)

    def node_output_bound_nodes(
        self,
        node_outputs: List[NodeOutput] | None = None,
        no_grabbing: bool = False,
    ) -> List[Node]:
        """Get a list of nodes that are connected to the node_outputs of this node.

        Parameters
        ----------
        node_outputs: List[NodeOutput] | None
            The node_outputs to check. If None, all node_outputs are used.

        Returns
        -------
        List[Node]: A list of nodes that are connected to the node_outputs

        """

        nodes: List[Node] = []
        if node_outputs is None:
            node_outputs = self._outputs
        for node_output in node_outputs:
            for edge in node_output.get_edges():
                if no_grabbing and edge.is_grabbing():
                    continue
                node = edge.other_node(self)
                nodes.append(node)
        return nodes

    def node_input_bound_nodes(
        self,
        node_inputs: List[NodeInput] | None = None,
        no_grabbing: bool = False,
    ) -> List[Node]:
        """Get a list of nodes that are connected to the node_inputs of this node.

        Parameters
        ----------
        node_inputs: List[NodeInput] | None
            The node_inputs to check. If None, all node_inputs are used.

        Returns
        -------
        List[Node]: A list of nodes that are connected to the node_inputs

        """

        nodes: List[Node] = []
        if node_inputs is None:
            node_inputs = self._inputs
        for node_input in node_inputs:
            for edge in node_input.get_edges():
                if no_grabbing and edge.is_grabbing():
                    continue
                node = edge.other_node(self)
                nodes.append(node)
        return nodes

    def _remove_io(self, io: NodeIO) -> bool:
        """Remove an io from the node.

        Parameters
        ----------
        io: NodeIO
            The io to remove

        Returns
        -------
        bool: True if the io was removed, False if not

        Raises
        ------
        IOError: If the io is not of type NodeIO or is not in the node

        """

        if not isinstance(io, NodeIO):
            raise NodeIOError(
                f"only NodeIO objects can be removed from Nodes, not '{type(io)}'"
            )
        if io.id not in self._io:
            raise NodeIOError(f"IO '{io.id}' not in node '{self.name}'")

        del self._io[io.id]
        io.remove()
        self.emit("remove_io", Message_Node_RemoveIO(io=io))
        return True

    def remove_input(self, node_input: NodeInput) -> bool:
        """Remove an node_input from the node.

        Parameters
        ----------
        node_input: NodeInput
            The node_input to remove

        Returns
        -------
        bool: True if the node_input was removed, False if not

        Raises
        ------
        IOError: If the node_input is not of type NodeInput or is not in the node
        """
        if not isinstance(node_input, NodeInput):
            raise NodeIOError(
                f"only NodeInput objects can be removed from Nodes, not '{type(node_input)}'"
            )
        if node_input not in self._inputs:
            raise NodeIOError(f"node_input '{node_input.id}' not in node '{self.name}'")

        self._inputs.remove(node_input)
        return self._remove_io(node_input)

    def remove_output(self, node_output: NodeOutput) -> bool:
        """Remove an node_output from the node.

        Parameters
        ----------
        node_output: NodeOutput
            The node_output to remove

        Returns
        -------
        bool: True if the node_output was removed, False if not

        Raises
        ------
        IOError: If the node_output is not of type NodeOutput or is not in the node
        """
        if not isinstance(node_output, NodeOutput):
            raise NodeIOError(
                f"only NodeOutput objects can be removed from Nodes, not '{type(node_output)}'"
            )
        if node_output not in self._outputs:
            raise NodeIOError(
                f"node_output '{node_output.id}' not in node '{self.name}'"
            )

        self._outputs.remove(node_output)
        return self._remove_io(node_output)

    def has_input(self, node_input: NodeInput) -> bool:
        """Check if the node has an node_input.

        Parameters
        ----------
        node_input: NodeInput
            The node_input to check

        Returns
        -------
        bool: True if the node_input is in the node, False if not
        """
        return node_input in self._inputs

    def has_output(self, node_output: NodeOutput) -> bool:
        """Check if the node has an node_output.

        Parameters
        ----------
        node_output: NodeOutput
            The node_output to check

        Returns
        -------
        bool: True if the node_output is in the node, False if not
        """

        return node_output in self._outputs

    def remove_io(self, io: NodeIO) -> bool:
        """Remove an io from the node.

        Parameters
        ----------
        io: NodeIO
            The io to remove

        Returns
        -------
        bool: True if the io was removed, False if not

        Raises
        ------
        NodeError: If the io is not of type NodeIO or is not in the node

        """
        if isinstance(io, NodeInput) and self.has_input(io):
            return self.remove_input(io)
        if isinstance(io, NodeOutput) and self.has_output(io):
            return self.remove_output(io)

        raise NodeError(f"IO '{io.id}' not found in node '{self.name}'")

    def get_input(self, input_id: NodeIOId) -> NodeInput:
        """Get an node_input by id.

        Parameters
        ----------
        input_id: NodeInputName
            The id of the node_input

        Returns
        -------
        NodeInput: The node_input

        Raises
        ------
        NodeIOError: If the node_input is not found
        TypeError: If the node_input is not of type NodeInput

        """
        node_input = self.get_input_or_output(input_id)

        if node_input is None or node_input not in self._inputs:
            raise NodeIOError(
                f"node_input '{input_id}' not found in node '{self.name}'"
            )

        if not isinstance(node_input, NodeInput):
            raise TypeError(f"node_input '{input_id}' is not of type NodeInput")

        return node_input

    def get_output(self, output_id: NodeIOId) -> NodeOutput:
        """Get an node_output by id.

        Parameters
        ----------
        output_id: NodeOutputName
            The id of the node_output

        Returns
        -------
        NodeOutput: The node_output

        Raises
        ------
        NodeIOError: If the node_output is not found
        TypeError: If the node_output is not of type NodeOutput
        """
        output = self.get_input_or_output(output_id)
        if output is None or output not in self._outputs:
            raise NodeIOError(
                f"node_output '{output_id}' not found in node '{self.name}'"
            )

        if not isinstance(output, NodeOutput):
            raise TypeError(f"node_output '{output_id}' is not of type NodeOutput")

        return output

    def get_inputs(self) -> List[NodeInput]:
        """Get all node_inputs of the node.

        Returns
        -------
        List[NodeInput]: The node_inputs

        """
        return [ip for ip in self._inputs]

    def get_outputs(self) -> List[NodeOutput]:
        """Get all node_outputs of the node.

        Returns
        -------
        List[NodeOutput]: The node_outputs

        """
        return [op for op in self._outputs]

    def get_edges(self) -> Set[Edge]:
        """Get all edges connected to the node.

        Returns
        -------
        List[Edge]: The edges connected to the node's inputs and outputs
        """
        edges = set()
        for io in self.get_inputs() + self.get_outputs():
            edges.update(io.get_edges())

        return edges

    def has_grabbing_input(self) -> bool:
        """Check if the node has a grabbing input.

        Returns
        -------
        bool: True if the node has a grabbing input, False if not
        """
        for ip in self.get_inputs():
            if ip.is_grabbing_input():
                return True

        return False

    def get_grabbable_inputs(self) -> List[NodeInput]:
        """Get all grabbing inputs of the node.

        Returns
        -------
        List[NodeInput]: The grabbable inputs
        """

        return [ip for ip in self.get_inputs() if ip.is_grabbing_input()]

    async def _trigger_grabbing_inputs(self):
        """Trigger all grabbing inputs of the node."""
        other_outputs: Set[NodeIO] = set()
        for ip in self.get_grabbable_inputs():
            other_outputs.update(ip.get_other_io())

        triggernodes: Set[Node] = set()
        for output in other_outputs:
            if output.node is None:
                continue
            if output.node.has_grabbing_input():
                triggernodes.add(output.node)
            if output.trigger_on_get:
                triggernodes.add(output.node)

        triggers = []
        for node in triggernodes:
            node.trigger()
            triggers.append(node.await_done())

        await asyncio.gather(*triggers)

        for ip in self.get_grabbable_inputs():
            ip.update_value(mark_for_trigger=False)

    # endregion IO

    # region Data

    def get_data(self, data_id: NodeDataName) -> Any:
        """Get the data of the node.

        Parameters
        ----------
        data_id: NodeDataName
            The id of the data to get

        Returns
        -------
        Any: The data or None if not found

        """

        return self._data.get(data_id, None)

    def get_all_data(self) -> NodeDataDict:
        """Get all data of the node.

        Returns
        -------
        Dict[NodeDataName, Any]: The data

        """
        return {k: v for k, v in self._data.items()}

    def _set_data(self, name: NodeDataName, value: Any, quiet: bool = False):
        """base method for setting data (internally called)

        Parameters
        ----------
        name: NodeDataName
            The name of the data to set
        value: Any
            The value to set
        quiet: bool
            If True, no signals are emitted
        """
        # base method for setting data (internally called)
        # if the data is set via an node_input or node_output, use the respective method
        old = self.get_data(name)
        self._data[name] = copy.deepcopy(value)
        self.logger.info("set data '%s' to '%s'", name, value)
        if not quiet:
            self.emit(
                "set.data",
                Message_Node_SetData(
                    name=name,
                    old=old,
                    new=value,
                ),
            )

    def get_state(self) -> NodeStateInterface:
        """Get the state of the node."""

        state = NodeStateInterface(
            inputs={nio.id: nio.state for nio in self._inputs},
            outputs={nio.id: nio.state for nio in self._outputs},
            data=self.get_all_data(),
            status=self.check_status(quiet=True),
        )
        return state

    # endregion Data

    # region Serialization

    def serialize(self) -> NodeSerializationInterface:
        """
        returns a json serializable dict of the node
        """
        full_properties: NodeProperties = self.properties
        default_properties = self.set_default_properties({})

        del full_properties["io"]

        deep_remove_dict_on_equal(full_properties, default_properties)  # type: ignore
        # add io serialization
        iodict: PropIODict = PropIODict()
        iodict["ip"] = {}
        iodict["op"] = {}
        full_properties["io"] = iodict
        for node_input in self._inputs:
            # serialize the node_input
            ioser = node_input.serialize()
            # remove the id, since it is not needed
            del ioser["id"]  # type: ignore
            # check if the node_input has a default value
            if hasattr(self, "__default_io_" + node_input.id):
                defaultio = getattr(self, "__default_io_" + node_input.id)
                # remove the default values from the serialization
                deep_remove_dict_on_equal(ioser, defaultio.serialize())  # type: ignore
                # if the serialization is empty, skip it
                if len(ioser) == 0:
                    continue
            iodict["ip"][node_input.id] = ioser
        # if all node_inputs are empty, remove the ip dict
        if len(iodict["ip"]) == 0:
            del iodict["ip"]

        for node_output in self._outputs:
            # serialize the node_output
            ioser = node_output.serialize()
            # remove the id, since it is not needed
            del ioser["id"]  # type: ignore
            # check if the node_output has a default value
            if hasattr(self, "__default_io_" + node_output.id):
                defaultio = getattr(self, "__default_io_" + node_output.id)
                # remove the default values from the serialization
                deep_remove_dict_on_equal(ioser, defaultio.serialize())  # type: ignore
                # if the serialization is empty, skip it
                if len(ioser) == 0:
                    continue
            iodict["op"][node_output.id] = ioser

        # if all node_outputs are empty, remove the op dict
        if len(full_properties["io"]["op"]) == 0:
            del full_properties["io"]["op"]

        # if all io dicts are empty, remove the io dict
        if len(full_properties["io"]) == 0:
            del full_properties["io"]

        if len(self.requirements) > 0:
            full_properties["requirements"] = self.requirements

        ser = NodeSerializationInterface(**full_properties, nid=self.node_id)
        return ser

    def full_serialize(self) -> FullNodeJSON:
        ser: FullNodeJSON = {
            "name": self.name,
            "id": self.id,
            "node_id": self.node_id,
            "io": {k: v.full_serialize() for k, v in self._io.items()},
            "data": self.get_all_data(),
            "requirements": self.requirements,
            "disabled": self.disabled,
            "status": {
                "operable": False,
                "disabled": True,
                "ready": False,
                "miss_inputs": [],
                "miss_data": [],
                "is_working": False,
                "has_trigger_request": False,
            },
        }
        if self.initialized:
            ser["status"] = self.check_status(quiet=True)

        return ser

    def _repr_json_(self):
        return {
            "name": self.name,
            "id": self.id,
            "node_id": self.node_id,
            "inputs": [nio.id for nio in self._inputs],
            "outputs": [nio.id for nio in self._outputs],
            "io": {k: v._repr_json_() for k, v in self._io.items()},
            "requirements": self.requirements,
        }

    # endregion Serialization

    # region trigger
    def _handle_trigger_task(self):
        """Handles the trigger task and raises exceptions if needed
        is called in multiple trigger relevant functions
        """
        if self._triggertask is not None:
            if self._triggertask.done():
                ex = self._triggertask.exception()
                self._triggertask = None
                self._in_trigger = False

                if ex is not None:
                    raise ex

            else:
                self._in_trigger = True
        else:
            self._in_trigger = False

    def request_trigger(self, src: str | None):
        """Request a trigger from the node
        The node will not be triggered directly but can be via trigger_if_requested

        Parameters
        ----------
        src : str | None
            The source of the request
        """

        if src is not None:
            self.logger.info("request trigger from '%s'", src)

        self._request_trigger = True

    def request_trigger_and_trigger(
        self, src: str | None, trigger_queue: TriggerQueue | None = None
    ) -> None | TriggerQueue:
        """Request a trigger from the node and trigger it directly

        Parameters
        ----------
        src : str | None
            The source of the request
        """
        self.request_trigger(src)
        if self.initialized:
            return self.trigger_if_requested(trigger_queue)

    @requires_init
    def check_status(self, quiet=False) -> NodeStatus:
        """Checks the status of the node and returns a NodeStatus object"""

        miss_inputs: List[NodeIOId] = []
        miss_data: List[NodeDataName] = []
        for node_input in self._inputs:
            if node_input.required:
                if node_input.length == 0:
                    miss_inputs.append(node_input.id)
                if node_input.value_or_none is None:
                    miss_data.append(node_input.id)

        stat = NodeStatus(
            operable=self.operable,
            disabled=self.disabled,
            ready=self.ready,
            miss_inputs=miss_inputs,
            miss_data=miss_data,
            is_working=self.is_working,
            has_trigger_request=self.has_trigger_request,
        )
        if not quiet:
            self.emit("check.status", Message_Node_CheckStatus(**stat))
        return stat

    def is_operable(self) -> Tuple[bool, str]:
        """Returns True if the node is operable"""
        if not self.initialized:
            return False, "node is not initialized"

        # check if all required node_inputs are set
        for node_input in self._inputs:
            if not node_input.ready:
                return (
                    False,
                    f"node_input '{node_input.id}' is not ready: {node_input.is_ready()[1]}",
                )
        return True, ""

    @abstractmethod
    async def on_trigger(self) -> bool:
        """The trigger function of the node
        This function is called when the node is triggered.
        It is async bu default but for now sync functions are also supported
        Should Return if the node was triggered successfully
        For now everything returned but False is considered as success

        """

    @requires_init
    def trigger_all_outputs_if_requested(
        self, trigger_queue: TriggerQueue | None = None
    ):
        """Triggers all node_outputs if requested"""
        for node in self.node_output_bound_nodes(no_grabbing=True):
            if node.operable and node.enabled:
                node.trigger_if_requested(trigger_queue)

    def _post_trigger_success(self, result: Any, trigger_queue: TriggerQueue):
        """Called after a trigger without an exception.
        here:
        - push all node_outputs,w/o mark_for_trigger
        - trigger all node_outputs if requested

        Parameters
        ----------
        result : Any
            The result of the trigger function, everything but False is considered as success
        """
        if result is False:
            return
        self.logger.debug("trigger success")
        # self.push_all_outputs(mark_for_trigger=False) # should be handeled by the output
        self.trigger_all_outputs_if_requested(trigger_queue)

    def _post_trigger(self, trigger_queue: TriggerQueue):
        """Called after a trigger, no matter if it was successful or not
        here:
        - reset the trigger flag
        - reset node_output changed
        - check status
        - trigger if requested
        """
        self.emit("trigger_done")
        self._in_trigger = False
        self.check_status(quiet=True)
        return self.trigger_if_requested(trigger_queue)

    @requires_init
    def trigger_if_requested(
        self, trigger_queue: TriggerQueue | None = None
    ) -> None | TriggerQueue:
        """Triggers the node if requested
        Returns if the node was triggered
        """
        if not self.operable:
            return None
        if self.has_trigger_request:
            return self.trigger(trigger_queue=trigger_queue)
        return None

    @requires_init
    def trigger(
        self, *args, trigger_queue: TriggerQueue | None = None, **kwargs
    ) -> None | TriggerQueue:
        """Triggers the node
        for this the Node has to be:
        - operable
        - not disabled
        - not working

        if the last trigger was to fast the trigger is delayed.
        See min_trigger_interval


        Returns if the node was triggered
        """
        if not self.operable:
            self.error(
                NotOperableException(
                    f"cannot trigger {self}, not operable:{self.is_operable()[1]}"
                )
            )
            return None

        if self.disabled:
            self.error(DisabledException(f"cannot trigger {self}, disabled"))
            return None

        if self.is_working:
            self.logger.debug("is working")
            self.request_trigger("working but trigger")
            if self._triggertask is not None:
                return self._triggertask.trigger_queue

        if trigger_queue is None:
            trigger_queue = TriggerQueue()

        _time = _deltatimer() * 1000
        loop = asyncio.get_event_loop()

        # now the real trigger starts
        self._in_trigger = True
        dtime = _time - self._last_trigger_time
        self._last_trigger_time = _time
        self._request_trigger = False
        self.emit("trigger")

        async def _trigger():
            if trigger_queue is None:
                return
            if self._triggerdelay > 0:
                await asyncio.sleep(self._triggerdelay / 1000)
            if dtime < self.min_trigger_interval:
                wait = self.min_trigger_interval - dtime
                self.logger.debug(f"trigger to fast,delay {wait} ms")
                await asyncio.sleep(wait / 1000)

            try:
                try:
                    await self._trigger_grabbing_inputs()
                    res = self.on_trigger(*args, **kwargs)
                    if asyncio.iscoroutine(res):
                        res = await res

                    self._post_trigger_success(res, trigger_queue)

                except Exception as err:  # pylint: disable=broad-except
                    raise TriggerException(f"trigger failed for {self}: {err}") from err
            except TriggerException as err:
                self.error(err)

            finally:
                self._post_trigger(trigger_queue=trigger_queue)

        self._triggertask = TriggerTask(loop.create_task(_trigger()))
        trigger_queue.append(self._triggertask)
        return trigger_queue

    def cancel_trigger(self):
        """
        cancel the current trigger process and open request
        """
        self._request_trigger = False
        if self._triggertask is not None:
            self._triggertask.cancel()

    async def await_done(self, timeout: float | None = 10, sleep: float = 0.01):
        """
        wait until node is done with its trigger processes and whatever results in a working state
        the node is triggered if requested before waiting and during waiting
        if the timeout is reached a TimeoutError is raised

        Parameters
        ----------
        timeout : float, optional
            timeout in seconds, by default None
        sleep : float, optional
            delta time between checks, by default 0.05

        """
        self.trigger_if_requested()
        start = _deltatimer()
        while True:
            if not self.is_working:
                self.trigger_if_requested()
            else:
                await asyncio.sleep(sleep)
            if not self.is_working:
                break

            if timeout is not None:
                if _deltatimer() - start > timeout:
                    raise TimeoutError("await_done timeout")

        self._handle_trigger_task()

    @staticmethod
    async def await_all(*nodes: Node, timeout: float = -1, sleep: float = 0.01):
        """
        wait until all nodes are done with their trigger processes and whatever
        results in a working state
        the nodes are triggered if requested before waiting and during waiting
        if the timeout is reached a TimeoutError is raised

        Parameters
        ----------
        *nodes : Node
            nodes to wait for
        timeout : float, optional
            timeout in seconds, by default None
        sleep : float, optional
            delta time between checks, by default 0.05
        """
        for node in nodes:
            node.trigger_if_requested()
        start = _deltatimer()
        while any((node.is_working for node in nodes)):
            await asyncio.sleep(sleep)
            for node in nodes:
                if not node.is_working:
                    node.trigger_if_requested()

            if timeout > 0:
                if _deltatimer() - start > timeout:
                    raise TimeoutError("await_all timeout")

    # endregion trigger

    @classmethod
    def get_source(cls) -> str:
        """returns the source code of the node"""
        return inspect.getsource(cls)

    @classmethod
    def get_required_imports(cls) -> list[str]:
        """returns the required imports of the node"""
        return [
            "from " + Node.__module__ + " import Node",
            "from " + NodeInput.__module__ + " import NodeInput",
            "from " + NodeOutput.__module__ + " import NodeOutput",
        ]

    @classmethod
    def full_class_serialize(cls) -> FullNodeClassJSON:
        """returns a dict with all information to recreate the node class"""
        return {
            "name": cls.__name__,
            "node_id": cls.node_id,
            "trigger_on_create": cls.trigger_on_create,
        }
