from __future__ import annotations
from typing import List, Dict, Type, Any, TypedDict, TYPE_CHECKING
import json
import copy
from .mixins import EventEmitterMixin, ObjectLoggerMixin, ProxyableMixin
from .errors import LibraryTypeError, NodeTypeError, LibraryError, NodeSpaceError
from .node import Node, NodeSerializationInterface, FullNodeClassJSON, FullNodeJSON

from ._typing import (
    LibShelf,
    NodeIdType,
    Message_NodeSpace_AddNode,
    Message_NodeSpace_RemoveNode,
    Message_NodeSpace_AddEdge,
    Message_NodeSpace_RemoveEdge,
    EventCallback,
    Message_Node_NewConnection,
)

from .node_detector import find_node_id

if TYPE_CHECKING:
    from .io import Edge
    from .io import EdgeSerializationInterface


class NodeSpaceSerializationInterface(TypedDict, total=False):
    """
    NodeSpaceSerializationInterface is the interface for the serialization of a NodeSpace
    """

    nodes: List[NodeSerializationInterface]
    edges: List[EdgeSerializationInterface]
    prop: Dict[str, Any]


class FullLibShelfJSON(TypedDict):
    name: str
    shelves: List[FullLibShelfJSON]
    nodes: List[FullNodeClassJSON]


class FullLibJSON(TypedDict):
    """
    FullLibJSON for a full serilization including temporary properties
    """

    shelves: List[FullLibShelfJSON]


class FullNodeSpaceJSON(TypedDict):
    """
    FullNodeSpaceJSON for a full serilization including temporary properties
    """

    nodes: List[FullNodeJSON]
    edges: List[FullEdgeJSON]
    prop: Dict[str, Any]
    lib: FullLibJSON


class Library(ProxyableMixin):
    """Library is a class that holds all the nodes that can be used in a nodespace.
    Nodeclasses can be sorted in shelves. shelves are just strings that can be used
    to group nodes together. shelves can be nested by using an array of strings.
    """

    def __init__(self):
        super().__init__()
        self._shelves: List[LibShelf] = []

    @property
    def shelves(self) -> List[LibShelf]:
        return copy.deepcopy(self._shelves)

    @property
    def available_nodes(self) -> Dict[NodeIdType, Type[Node]]:
        """
        available_nodes returns a dictionary of all available nodes
        """
        nodes: Dict[NodeIdType, Type[Node]] = {}

        def _traverse_shelf(shelf: LibShelf):
            for node in shelf["nodes"]:
                nodes[node.node_id] = node
            for subshelf in shelf["shelves"]:
                _traverse_shelf(subshelf)

        for shelf in self._shelves:
            _traverse_shelf(shelf)

        return nodes

    def _get_subshelf(
        self,
        subname: str,
        current_shelf: LibShelf | None = None,
    ) -> LibShelf | None:
        """
        get_subshelf returns the subshelf with the given name or None if it does not exist

        Parameters
        ----------
        current_shelf : LibShelf|None
            the current shelf or the base shelves
        subname : str
            the name of the subshelf

        Returns
        -------
        LibShelf | None
            the subshelf or None if it does not exist
        """
        shelves: List[LibShelf]
        if current_shelf is None:
            shelves = self._shelves
        else:
            shelves = current_shelf["shelves"]

        for shelf in shelves:
            if shelf["name"] == subname:
                return shelf
        return None

    def _get_or_create_subshelf(
        self, subname: str, current_shelf: LibShelf | None = None
    ) -> LibShelf:
        """
        get_or_create_subshelf returns the subshelf with the given name
        or creates it if it does not exist

        Parameters
        ----------
        current_shelf : LibShelf|None
            the current shelf or the base shelves
        subname : str
            the name of the subshelf

        Returns
        -------
        LibShelf
            the subshelf
        """

        shelves: List[LibShelf]
        if current_shelf is None:
            shelves = self._shelves
        else:
            shelves = current_shelf["shelves"]

        shelf = self._get_subshelf(subname, current_shelf)
        if shelf is None:
            shelf = LibShelf(name=subname, nodes=[], shelves=[])
            shelves.append(shelf)
        return shelf

    def _get_deep_shelf(
        self, shelf: List[str], current_shelf: LibShelf | None = None
    ) -> LibShelf:
        """
        get_deep_shelf returns the deep shelf with the given name
        or creates it if it does not exist

        Parameters
        ----------
        shelf : List[str]
            the names of the subshelves
         current_shelf : LibShelf | None
            the current shelf or the base shelves

        Returns
        -------
        LibShelf:
            the subshelf

        Raises
        ------
        TypeError
            if shelf is not an array of strings

        """
        if not isinstance(shelf, list):
            raise LibraryTypeError("shelf must be an array of strings")

        for s in shelf:
            if not isinstance(s, str):
                raise LibraryTypeError("shelf keys must be a string")

        if len(shelf) == 0:
            if current_shelf is None:
                raise LibraryError("shelf cannot be empty if current_shelf is None")
            return current_shelf

        subshelf: LibShelf = self._get_or_create_subshelf(shelf[0], current_shelf)
        if len(shelf) == 1:
            return subshelf

        return self._get_deep_shelf(shelf[1:], subshelf)

    def add_nodeclass(
        self, nodeclass: Type[Node], shelf: str | List[str] | None = None
    ):
        """add_nodeclass adds the given nodeclass to the library

        Parameters
        ----------
        nodeclass : Type[Node]
            the nodeclass to add
        shelf : str | List[str]
            the shelf to add the nodeclass to, can be a nested shelf by using an array of strings

        Raises
        ------
        TypeError
            if nodeclass is not a subclass of Node
        ValueError
            if nodeclass with same id is already in the library and is not the same class
        TypeError
            if shelf is not a string or array of strings

        """
        if not issubclass(nodeclass, Node):
            raise NodeTypeError(
                f"nodeclass must be a subclass of Node, not {nodeclass}"
            )

        available_nodes = self.available_nodes
        if nodeclass.node_id in available_nodes:
            if available_nodes[nodeclass.node_id] != nodeclass:
                raise LibraryError(
                    f"nodeclass {nodeclass.node_id} already exists in library and is not the same class"
                )

        if shelf is None:
            shelf = ["default"]
        # If shelf is a string, convert it to an array.
        if isinstance(shelf, str):
            shelf = [shelf]

        if len(shelf) == 0:
            shelf = ["default"]
        target_shelf: LibShelf = self._get_deep_shelf(shelf)
        target_shelf["nodes"].append(nodeclass)

    def add_nodeclasses(
        self,
        nodes: List[Type[Node]] | LibShelf,
        shelf: str | List[str] | None = None,
    ):
        """add_nodeclasses adds the given nodeclasses to the library

        Parameters
        ----------
        nodes : List[Type[Node]] | LibShelf
            the nodeclasses to add, can be an array of nodeclasses or an object with shelves
            If it is an object with shelves, the shelves will be added to the library under the
            shelf argument.
        shelf : str | List[str]
            the shelf to add the nodeclasses to, can be a nested shelf by using an array of strings.
            If nodes is an object with shelves, this argument will be used as the parent shelf.
            If it is None, the shelves will be added to the root shelf
            and lists of nodes will be added to the "default" shelf.

        Raises
        ------
        TypeError
            if nodes is not an array of nodeclasses or an object with shelves
        TypeError
            if shelf is not a string or array of strings
        TypeError
            if values of a shelf are not a subclass of Node or a shelf
        """
        if isinstance(shelf, str):
            shelf = [shelf]
        if isinstance(nodes, list):
            for node in nodes:
                self.add_nodeclass(node, shelf)
        elif isinstance(nodes, dict):
            if "name" not in nodes:
                raise LibraryError("shelf must have a name")
            subsubs: List[str] = []
            if isinstance(shelf, str):
                subsubs = [shelf]
            elif isinstance(shelf, list):
                subsubs = [s for s in shelf]
            elif shelf is None:
                subsubs = []
            else:
                raise LibraryTypeError(
                    "shelf must be a string or array of strings or None"
                )
            subsubs.append(nodes["name"])

            if "nodes" in nodes:
                for node in nodes["nodes"]:
                    self.add_nodeclass(node, subsubs)
            if "shelves" in nodes:
                for subshelf in nodes["shelves"]:
                    self.add_nodeclasses(subshelf, subsubs)

    def contains_nodeclass(self, nodeclass: Type[Node]) -> bool:
        """Returns true if the library contains the given nodeclass

        Parameters
        ----------
        nodeclass : Type[Node]
            the nodeclass to check

        Returns
        -------
        bool
            true if the library contains the given nodeclass

        Raises
        ------
        TypeError
            if nodeclass is not a subclass of Node
        """
        # check if nodeclass is a subclass of Node
        if not issubclass(nodeclass, Node):
            raise LibraryTypeError(
                f"nodeclass must be a subclass of Node, not {nodeclass}"
            )
        return nodeclass.node_id in self.available_nodes

    def get_node_by_id(self, node_id: NodeIdType) -> Type[Node] | None:
        """get_node_by_id returns the nodeclass with the given id or None
        if it does not exist

        Parameters
        ----------
        node_id : NodeIdType
            the id of the nodeclass

        Returns
        -------
        Type[Node]| None
            the nodeclass with the given id or None if it does not exist
        """
        if not isinstance(node_id, NodeIdType):
            raise LibraryTypeError(
                f"node_id must be a NodeIdType not {node_id}(type {type(node_id)}))"
            )
        return self.available_nodes.get(node_id)

    def has_node_id(self, node_id: NodeIdType) -> bool:
        """has_node_id returns true if the library contains a nodeclass with the given id

        Parameters
        ----------
        node_id : NodeIdType
            the id of the nodeclass

        Returns
        -------
        bool
            true if the library contains a nodeclass with the given id
        """
        if not isinstance(node_id, NodeIdType):
            raise LibraryTypeError(
                f"node_id must be a NodeIdType not {node_id}(type {type(node_id)}))"
            )
        return node_id in self.available_nodes

    def add_shelf_by_node_id(self, node_id: NodeIdType) -> bool:
        """
        adds a node by a node id. return True if a new shelfe was added, False if the node is already in the lib.
        Raises a LibraryError if the node was not found
        """
        if not self.has_node_id(node_id):
            shelf = find_node_id(node_id)
            if shelf is not None:
                self.add_nodeclasses(shelf)
                return True
            raise LibraryError(f"node with id {node_id} not found")
        return False

    def full_serialize(self) -> FullLibJSON:
        """full_serialize returns a full serialization of the library

        Returns
        -------
        FullLibJSON
            a full serialization of the library
        """

        def _full_serialize_shelf(shelf: LibShelf) -> FullLibShelfJSON:
            return {
                "name": shelf["name"],
                "nodes": [node.full_class_serialize() for node in shelf["nodes"]],
                "shelves": [
                    _full_serialize_shelf(subshelf) for subshelf in shelf["shelves"]
                ],
            }

        parent_shelves: List[FullLibShelfJSON] = [
            _full_serialize_shelf(shelf) for shelf in self.shelves
        ]
        return {
            "shelves": parent_shelves,
        }

    def remove_nodeclass(self, nodeclass: Type[Node]):
        """remove_nodeclass removes the given nodeclass from the library

        Parameters
        ----------
        nodeclass : Type[Node]
            the nodeclass to remove

        Raises
        ------
        TypeError
            if nodeclass is not a nodeclass
        """
        if not issubclass(nodeclass, Node):
            raise LibraryTypeError(
                f"nodeclass must be a subclass of Node, not {nodeclass}"
            )
        if nodeclass.node_id not in self.available_nodes:
            return

        def _remove_from_shelf(shelf: LibShelf) -> None:
            if nodeclass in shelf["nodes"]:
                shelf["nodes"].remove(nodeclass)
            for subshelf in shelf["shelves"]:
                _remove_from_shelf(subshelf)

        for shelf in self.shelves:
            _remove_from_shelf(shelf)

    def remove_nodeclasses(self, nodeclasses: List[Type[Node]]) -> None:
        """remove_nodeclasses removes the given nodeclasses from the library

        Parameters
        ----------
        nodeclasses : List[Type[Node]]
            the nodeclasses to remove

        Raises
        ------
        TypeError
            if nodeclasses is not a list of nodeclasses
        """
        for nodeclass in nodeclasses:
            self.remove_nodeclass(nodeclass)

    def _repr_json_(self) -> FullLibJSON:
        return self.full_serialize()


DEFAULT_LIB: Library = Library()


class NodeSpace(EventEmitterMixin, ObjectLoggerMixin, ProxyableMixin):
    """NodeSpace is a collection of nodes that can be used to create functional graph"""

    def __init__(self, lib: Library | None = None):
        super().__init__()
        self._nodes: Dict[NodeIdType, Node] = {}
        self._global_triggerdelay = 0
        if lib is None:
            lib = Library()
            default_shelves = DEFAULT_LIB.shelves
            for shelf in default_shelves:
                lib.add_nodeclasses(shelf)
        self.lib = lib

        self._properties: Dict[str, Any] = {}

    # region Properties
    @property
    def lib(self) -> Library:
        """lib is the library of nodes that can be used in this nodespace

        Returns
        -------
        Library
            the library of nodes that can be used in this nodespace

        Raises
        ------
        TypeError
            if lib is not a Library

        Notes
        -----
        The library can be set to a new library, but it must be a Library

        Examples
        --------
        >>> nodespace = NodeSpace()
        >>> nodespace.lib = Library()
        >>> nodespace.lib = DEFAULT_LIB
        >>> nodespace.lib = "not a library"
        Traceback (most recent call last):
            ...
        TypeError: lib must be a Library


        """
        return self._lib

    @lib.setter
    def lib(self, lib: Library):
        if not isinstance(lib, Library):
            raise TypeError("lib must be a Library")
        self._lib = lib

    def set_property(self, name: str, value: Any):
        """set_property sets the property with the given name to the given value

        Parameters
        ----------
        name : str
            the name of the property
        value : Any
            the value of the property

        Raises
        ------
        TypeError
            if name is not a string

        Notes
        -----
        Properties are stored in a dictionary and can be used to store any data
        that is needed for the nodespace

        """
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        self._properties[name] = value

    def get_property(self, name: str) -> Any:
        """get_property returns the property with the given name or None if it does not exist

        Parameters
        ----------
        name : str
            the name of the property

        Returns
        -------
        Any
            the property with the given name or None if it does not exist

        Raises
        ------
        TypeError
            if name is not a string

        Notes
        -----
        Properties are stored in a dictionary and can be used to store any data
        that is needed for the nodespace

        """

        return self._properties.get(name)

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[Edge]:
        return self.get_edges()

    # endregion Properties

    # region Nodes
    def _register_node_listeners(self, node: Node):
        """_register_node_listeners registers the event listeners for the given node
        called on node add
        """
        new_connection_cb: EventCallback[
            Message_Node_NewConnection
        ] = self._node_new_connection
        node.on("new_connection", new_connection_cb)
        node.on_error(self._nodeerror)
        node.on("edge_removed", self._node_disconnected)

    def _unregister_node_listeners(self, node: Node):
        """_unregister_node_listeners unregisters the event listeners for the given node"""
        node.off("new_connection", self._node_new_connection)
        node.off_error(self._nodeerror)
        node.off("edge_removed", self._node_disconnected)

    # region Node Events
    def _nodeerror(self, error: Exception, src: Node):
        """_nodeerror handles the error event of a node and emits it as an error event of the NodeSpace"""
        error.node = src  # type: ignore
        self.error(error)

    def _node_new_connection(
        self,
        edge: Edge,
        src: Node,
    ):
        """_node_new_connection handles the new_connection event of a node
        To prevent double fireing of the event, for both sides of the edge,
        it only fires the event if the node is the start node of the edge
        """
        if edge.start_node == src:
            self.emit("edge_added", Message_NodeSpace_AddEdge(edge=edge))

    def _node_disconnected(self, edge: Edge, src: Node):
        """_node_disconnected handles the disconnected event of a node
         To prevent double fireing of the event, for both sides of the edge,
        it only fires the event if the node is the start node of the edge
        """
        if edge.start_node == src:
            self.emit("edge_removed", Message_NodeSpace_RemoveEdge(edge=edge))

    # endregion Node Events

    @EventEmitterMixin.catch_and_msg
    def add_node(self, node: Node) -> List[Node]:
        """adds a node the the nodespace
            All nodes that are connected to the given node will also be added
            (which usually hints to a strange workflow, but ok)

        Parameters
        ----------
        node : Node
            the node to add

        Returns
        -------
        List[Node]
            a list of all nodes that were added

        Raises
        ------
        TypeError
            if node is not of type Node
        TypeError
            if node is not in the node library
        TypeError
            if node is not of the correct type
        NodeSpaceError
            if a node with the same id already exists
        """
        if not isinstance(node, Node):
            raise NodeTypeError(f"node must be of type Node, not {type(node)}")
        if not self.lib.contains_nodeclass(node.__class__):
            raise LibraryError(f"node {node.__class__} is not in the node library")
        ncls = self.lib.get_node_by_id(node.__class__.node_id)
        if ncls is None:
            raise LibraryError(f"node {node.__class__} is not in the node library")
        if not isinstance(node, ncls):
            raise NodeTypeError(f"node {node.__class__} is not of the correct type")

        if node.id in self._nodes:
            if self._nodes[node.id] == node:
                return []
            raise NodeSpaceError(f"node {node.id} already exists")

        node.nodespace = self
        node.triggerdelay = self._global_triggerdelay
        self._nodes[node.id] = node
        self._register_node_listeners(node)
        self.emit("node_added", Message_NodeSpace_AddNode(node=node))

        if not node.initialized:
            node.initialize()

        ret = [node]
        # add all nodes that are connected to this node
        for ip in node.get_inputs():
            if ip.length == 0:
                continue
            other_ios = ip.get_other_io()
            for other_io in other_ios:
                other_node = other_io.node
                nodes: List[Node] | None = self.add_node(other_node)
                if nodes is not None:
                    ret.extend(nodes)

        for op in node.get_outputs():
            if op.length == 0:
                continue
            other_ios = op.get_other_io()
            for other_io in other_ios:
                other_node = other_io.node
                nodes: List[Node] | None = self.add_node(other_node)
                if nodes is not None:
                    ret.extend(nodes)

        return ret

    def has_node(self, node_id: NodeIdType) -> bool:
        """has_node returns True if the node with the given id exists

        Parameters
        ----------
        node_id : NodeIdType
            the id of the node

        Returns
        -------
        bool
            True if the node exists, False otherwise
        """
        return node_id in self._nodes

    def get_node(self, node_id: NodeIdType) -> Node:
        """get_node returns the node with the given id or None
        if it does not exist

        Parameters
        ----------
        node_id : NodeIdType
            the id of the node

        Returns
        -------
        Node
            the node with the given id

        Raises
        ------
        NodeSpaceError
            if the node does not exist
        TypeError
            if the resulting object is not a Node
        """
        if node_id not in self._nodes:
            raise NodeSpaceError(f"node {node_id} does not exist")

        node = self._nodes[node_id]
        if not isinstance(node, Node):
            raise NodeTypeError(f"node {node_id} is not of type Node")
        return node

    def remove_node(self, node: Node):
        """Removes a node from the nodespace

        Parameter
        ----------
        node : Node
            the node to remove

        Raises
        ------
        NodeSpaceError
            if the node does not exist
        TypeError
            if node is not of type Node
        """

        if not isinstance(node, Node):
            raise NodeTypeError(f"node must be of type Node, not {type(node)}")

        if node.id not in self._nodes:
            raise NodeSpaceError(f"node {node.id} does not exist")

        del self._nodes[node.id]

        node.remove()
        # remove the node
        self._unregister_node_listeners(node)

        self.emit("node_removed", Message_NodeSpace_RemoveNode(node=node))

    def remove_node_by_id(self, node_id: NodeIdType):
        """Removes a node from the nodespace by its id

        Parameter
        ----------
        node_id : NodeIdType
            the id of the node to remove
        """
        return self.remove_node(self.get_node(node_id))

    def empty(self):
        """empties the nodespace by removing all nodes"""
        nodes = list(self._nodes.values())
        for node in nodes:
            self.remove_node(node)
        self.emit("nodespace_cleared")

    def new_node(self, node_id: NodeIdType, node_data=None) -> Node:
        """new_node creates a new node of the given type

        Parameters
        ----------
        node_id : NodeIdType
            the id of the node to create

        Returns
        -------
        Node
            the created node

        Raises
        ------
        NodeSpaceError
            if the node does not exist
        """

        if self.lib.add_shelf_by_node_id(node_id):
            self.emit("node_library_updated")

        nodeclass = self._lib.get_node_by_id(node_id)
        if nodeclass is None:
            raise NodeSpaceError(f"nodeclass {node_id} not found in library")

        if node_data is None:
            node_data = {}

        node = nodeclass(**node_data)
        self.add_node(node)

        return node

    # endregion Nodes

    # region Connections
    def connect(
        self,
        start: Node,
        start_io: str,
        end: Node,
        end_io: str,
        replace_if_necessary: bool = False,
    ) -> Edge:
        """connect connects two nodes

        Parameters
        ----------
        start : Node
            the start node
        start_io : str
            the start io
        end : Node
            the end node
        end_io : str
            the end io
        replace_if_necessary : bool, optional
            if True, the connection will replace an existing connection
            if it hinderes the new connection, by default False


        Raises
        ------
        NodeSpaceError
            if the nodes do not exist
        NodeSpaceError
            if the nodes are not connected
        TypeError
            if start is not of type Node
        TypeError
            if end is not of type Node
        """
        if not isinstance(start, Node):
            raise NodeTypeError(f"start must be of type Node, not {type(start)}")
        if not isinstance(end, Node):
            raise NodeTypeError(f"end must be of type Node, not {type(end)}")

        if start.id not in self._nodes:
            raise NodeSpaceError(f"start node {start.id} does not exist")
        if end.id not in self._nodes:
            raise NodeSpaceError(f"end node {end.id} does not exist")

        if start_io not in start.io:
            raise NodeSpaceError(
                f"start io {start_io} does not exist, allowed are {', '.join(start.io.keys())}"
            )
        if end_io not in end.io:
            raise NodeSpaceError(
                f"end io {end_io} does not exist, allowed are {', '.join(end.io.keys())}"
            )

        return start.io[start_io].connect_to(
            end.io[end_io], replace_if_necessary=replace_if_necessary
        )

    def connect_by_id(
        self,
        start_id: NodeIdType,
        start_io: str,
        end_id: NodeIdType,
        end_io: str,
        replace_if_necessary: bool = False,
    ) -> Edge | None:
        """connect_by_id connects two nodes by their ids

        Parameters
        ----------
        start_id : NodeIdType
            the id of the start node
        start_io : str
            the start io
        end_id : NodeIdType
            the id of the end node
        end_io : str
            the end io
        replace_if_necessary : bool, optional
            if True, the connection will replace an existing connection
            if it hinderes the new connection, by default False
        """
        try:
            return self.connect(
                self.get_node(start_id),
                start_io,
                self.get_node(end_id),
                end_io,
                replace_if_necessary=replace_if_necessary,
            )
        except NodeSpaceError as exc:
            self.error(exc)

    def disconnect(self, start: Node, start_io: str, end: Node, end_io: str):
        """disconnect disconnects two nodes

        Parameters
        ----------
        start : Node
            the start node
        start_io : str
            the start io
        end : Node
            the end node
        end_io : str
            the end io

        Raises
        ------
        NodeSpaceError
            if the nodes do not exist
        NodeSpaceError
            if the nodes are not connected
        TypeError
            if start is not of type Node
        TypeError
            if end is not of type Node
        """
        if not isinstance(start, Node):
            raise NodeTypeError(f"start must be of type Node, not {type(start)}")
        if not isinstance(end, Node):
            raise NodeTypeError(f"end must be of type Node, not {type(end)}")

        if start.id not in self._nodes:
            raise NodeSpaceError(f"start node {start.id} does not exist")
        if end.id not in self._nodes:
            raise NodeSpaceError(f"end node {end.id} does not exist")

        start.io[start_io].disconnect_from(end.io[end_io])

    def disconnect_by_id(
        self,
        start_id: NodeIdType,
        start_io: str,
        end_id: NodeIdType,
        end_io: str,
    ):
        """disconnect_by_id disconnects two nodes by their ids

        Parameters
        ----------
        start_id : NodeIdType
            the id of the start node
        start_io : str
            the start io
        end_id : NodeIdType
            the id of the end node
        end_io : str
            the end io
        """
        self.disconnect(
            self.get_node(start_id),
            start_io,
            self.get_node(end_id),
            end_io,
        )

    def get_edges(self) -> List[Edge]:
        """edges returns all edges in the nodespace

        Returns
        -------
        List[Edge]
            the edges
        """
        ret = set()
        for id, node in self._nodes.items():
            ret.update(node.get_edges())
        return list(ret)

    # endregion Connections

    # region Serialization

    def serialize_nodes(self) -> List[NodeSerializationInterface]:
        """serialize_nodes serializes the nodes in the nodespace

        Returns
        -------
        List[NodeSerializationInterface]
            the serialized nodes
        """
        ret = []
        for name, node in self._nodes.items():
            ret.append(node.serialize())
        return json.loads(json.dumps(ret))

    def serialize_edges(
        self, nodes: List[NodeSerializationInterface]
    ) -> List[EdgeSerializationInterface]:
        """serialize_edges serializes the edges in the nodespace

        Returns
        -------
        List[EdgeSerializationInterface]
            the serialized edges
        """
        indexmap = {}
        for i, node in enumerate(nodes):
            indexmap[node["id"]] = i

        ret = []

        for edge in self.get_edges():
            if edge.start.node is None or edge.end.node is None:
                raise NodeSpaceError("edge has no start or end node")

            ret.append(
                (
                    edge.start.node.id,
                    edge.start.id,
                    edge.end.node.id,
                    edge.end.id,
                )
            )
        return json.loads(json.dumps(ret))

    def serialize(self) -> NodeSpaceSerializationInterface:
        """serialize serializes the nodespace to a dictionary

        Returns
        -------
        NodeSpaceSerializationInterface
            the serialized nodespace
        """
        nodes: List[NodeSerializationInterface] = self.serialize_nodes()
        ret = NodeSpaceSerializationInterface(
            nodes=nodes,
            edges=self.serialize_edges(nodes),
            prop=self._properties,
        )

        return json.loads(json.dumps(ret))

    def full_serialize(self) -> FullNodeSpaceJSON:
        return {
            "nodes": [node.full_serialize() for name, node in self._nodes.items()],
            "prop": self._properties,
            "lib": self.lib.full_serialize(),
            "edges": [e.full_serialize() for e in self.get_edges()],
        }

    def _repr_json_(self):
        return {
            "nodes": [node.id for name, node in self._nodes.items()],
            "prop": self._properties,
            "edges": [e.full_serialize() for e in self.get_edges()],
        }

    def deserialize(self, serialized: NodeSpaceSerializationInterface):
        """deserialize deserializes a serialized nodespace

        Parameters
        ----------
        serialized : NodeSpaceSerializationInterface
            the serialized nodespace

        Raises
        ------
        NodeSpaceError
            if a nodeclass is not found in the library

        """

        if not isinstance(serialized, dict):
            raise NodeSpaceError(
                f"serialized must be of type dict not {type(serialized)}"
            )

        self.empty()

        self._properties.update(serialized.get("prop", {}))
        nodes = serialized.get("nodes", [])
        edges = serialized.get("edges", [])

        for node in nodes:
            try:
                self.new_node(node["nid"], node_data=node)
            except NodeSpaceError as exc:
                self.error(exc)

        for edge in edges:
            try:
                if isinstance(edge[0], int):
                    startnodeid = nodes[edge[0]]["id"]
                else:
                    startnodeid = self.get_node(edge[0]).id

                if isinstance(edge[2], int):
                    endnodeid = nodes[edge[2]]["id"]
                else:
                    endnodeid = self.get_node(edge[2]).id

                self.connect_by_id(
                    startnodeid,
                    edge[1],
                    endnodeid,
                    edge[3],
                )
            except Exception as err:
                self.error(err)

        self.emit("deserialized")

    def deserialize_json(self, serialized: str):
        """deserialize_json deserializes a serialized nodespace from a json string

        Parameters
        ----------
        serialized : str
            the serialized nodespace

        Raises
        ------
        NodeSpaceError
            if a nodeclass is not found in the library

        """
        self.deserialize(json.loads(serialized))

    def serialize_json(self, *args, **kwargs) -> str:
        """serialize_json serializes the nodespace to a json string

        Returns
        -------
        str
            the serialized nodespace
        """
        return json.dumps(self.serialize(), *args, **kwargs)

    # endregion Serialization

    async def await_done(self, timeout: float = -1, sleep: float = 0.05):
        """await_done waits until all nodes are done

        Parameters
        ----------
        timeout : float | None, optional
            the timeout, by default 10
        sleep : float, optional
            the sleep time, by default 0.05
        """
        return await Node.await_all(*self.nodes, timeout=timeout, sleep=sleep)

    @property
    def is_working(self) -> bool:
        """returns if the nodespace is working"""
        any_node = any((node.is_working for node in self.nodes))
        return any_node
