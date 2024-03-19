from typing import List, Dict, TypedDict, Tuple, Any
import json
from uuid import uuid4
import traceback


from .node import (
    FullNodeJSON,
    NodeJSON,
    PlaceHolderNode,
    NodeTriggerError,
    Node,
    run_until_complete,
)  #
from .io import NodeInput, NodeOutput


from .lib import FullLibJSON, Library, NodeClassNotFoundError, Shelf


from .eventmanager import EventEmitterMixin, MessageInArgs, emit_after
from .utils.serialization import JSONEncoder, JSONDecoder


class NodeException(Exception):
    pass


class FullNodeSpaceJSON(TypedDict):
    """
    FullNodeSpaceJSON for a full serilization including temporary properties
    """

    nodes: List[FullNodeJSON]
    edges: List[Tuple[str, str, str, str]]
    prop: Dict[str, Any]
    lib: FullLibJSON


class NodeSpaceJSON(TypedDict, total=False):
    """
    NodeSpaceJSON is the interface for the serialization of a NodeSpace
    """

    nodes: List[NodeJSON]
    edges: List[Tuple[str, str, str, str]]
    prop: Dict[str, Any]


class NodeSpace(EventEmitterMixin):
    """
    NodeSpace is a collection of nodes and edges between them
    """

    def __init__(self, id: str | None = None):
        super().__init__()
        self._nodes: Dict[str, Node] = {}
        self._properties: Dict[str, Any] = {}
        self.lib = Library()
        if id is None:
            id = uuid4().hex
        self._id = id

    # region Properties
    @property
    def id(self) -> str:
        return self._id

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[Tuple[NodeOutput, NodeInput]]:
        edges: List[Tuple[NodeOutput, NodeInput]] = []
        for node in self.nodes:
            for output in node.outputs.values():
                for input in output.connections:
                    edges.append((output, input))

        return edges

    # endregion Properties

    # region serialization

    def full_serialize(self) -> FullNodeSpaceJSON:
        return {
            "nodes": [node.full_serialize() for node in self.nodes],
            "prop": self._properties,
            "lib": self.lib.full_serialize(),
            "edges": self.serialize_edges(),
        }

    def deserialize_nodes(self, data: List[NodeJSON]):
        """
        deserialize_nodes deserializes a list of nodes

        Parameters
        ----------
        data : List[NodeJSON]
            the nodes to deserialize

        Returns
        -------
        Dict[str, Node]
            the deserialized nodes
        """
        for node in self.nodes:
            self.remove_node_instance(node)
        for node in data:
            try:
                node_cls = self.lib.get_node_by_id(node["node_id"])
            except NodeClassNotFoundError:
                node_cls = PlaceHolderNode
            node_instance = node_cls()
            node_instance.deserialize(node)
            self.add_node_instance(node_instance)

    def deserialize_edges(self, data: List[Tuple[str, str, str, str]]):
        for output_uuid, output_id, input_uuid, input_id in data:
            try:
                output = self.get_node_by_id(output_uuid).get_input_or_output(output_id)
                input = self.get_node_by_id(input_uuid).get_input_or_output(input_id)
                if isinstance(output, NodeOutput) and isinstance(input, NodeInput):
                    input.connect(output)
                else:
                    output.connect(input)
            except Exception:
                pass

    def serialize_nodes(self) -> List[NodeJSON]:
        """serialize_nodes serializes the nodes in the nodespace

        Returns
        -------
        List[NodeJSON]
            the serialized nodes
        """
        ret = []
        for node in self.nodes:
            ret.append(node.serialize())
        return json.loads(json.dumps(ret, cls=JSONEncoder), cls=JSONDecoder)

    def serialize_edges(self) -> List[Tuple[str, str, str, str]]:
        return [
            (output.node.uuid, output.uuid, input.node.uuid, input.uuid)
            for output, input in self.edges
            if output.node is not None and input.node is not None
        ]

    def deserialize(self, data: NodeSpaceJSON):
        """
        deserialize deserializes the nodespace from a dictionary

        Parameters
        ----------
        data : NodeSpaceJSON
            the data to deserialize
        """
        self.clear()
        self._properties = data.get("prop", {})
        self.deserialize_nodes(data.get("nodes", []))
        self.deserialize_edges(data.get("edges", []))

    def serialize(self) -> NodeSpaceJSON:
        """serialize serializes the nodespace to a dictionary

        Returns
        -------
        NodeSpaceSerializationInterface
            the serialized nodespace
        """
        ret = NodeSpaceJSON(
            nodes=self.serialize_nodes(),
            edges=self.serialize_edges(),
            prop=self._properties,
        )
        return json.loads(json.dumps(ret, cls=JSONEncoder), cls=JSONDecoder)

    def clear(self):
        """clear removes all nodes and edges from the nodespace"""
        for node in self.nodes:
            self.remove_node_instance(node)

        self._properties = {}

    # endregion serialization

    # region nodes
    # region add/remove nodes

    def add_node_instance(self, node: Node):
        """add_node_instance adds a node instance to the nodespace

        Parameters
        ----------
        node : Node
            the node to add
        """
        if node.uuid in self._nodes:
            raise ValueError(f"node with uuid '{node.uuid}' already exists")
        self._nodes[node.uuid] = node
        node.on("*", self.on_node_event)
        node.on_error(self.on_node_error)
        node_ser = node.serialize()
        msg = MessageInArgs(node=node_ser)
        self.emit("node_added", msg)

        return node

    def on_node_event(self, event: str, src: Node, **data):
        msg = MessageInArgs(node=src.uuid, **data)
        self.emit(event, msg)

    def on_node_error(self, src: Node, error: Exception):
        key = "node_error"
        if isinstance(error, NodeTriggerError):
            key = "node_trigger_error"
        self.emit(
            key,
            MessageInArgs(
                node=src.uuid, error=error, tb=traceback.format_exception(error)
            ),
        )

    def remove_node_instance(self, node: Node) -> str:
        if node.uuid not in self._nodes:
            raise ValueError(f"node with uuid '{node.uuid}' not found in nodespace")

        node = self._nodes.pop(node.uuid)
        node.off("*", self.on_node_event)

        for output in node.outputs.values():
            for input in output.connections:
                if input.node is not None:
                    if input.node.uuid in self._nodes:
                        output.disconnect(input)
        for input in node.inputs.values():
            for output in input.connections:
                if output.node is not None:
                    if output.node.uuid in self._nodes:
                        output.disconnect(input)

        msg = MessageInArgs(node=node.uuid)
        self.emit("node_removed", msg)
        uuid = node.uuid
        node.prepdelete()
        del node
        return uuid

    def add_node_by_id(self, id: str, **kwargs):
        # find node in lib
        node_cls = self.lib.get_node_by_id(id)
        if node_cls is None:
            raise ValueError(f"node with id '{id}' not found in lib")

        node = node_cls(**kwargs)
        return self.add_node_instance(node)

    def remove_node_by_id(self, nid: str) -> str | None:
        try:
            return self.remove_node_instance(self.get_node_by_id(nid))
        except ValueError as e:
            pass

    # endregion add/remove nodes

    def get_node_by_id(self, nid: str) -> Node:
        if nid not in self._nodes:
            raise ValueError(f"node with id '{nid}' not found in nodespace")
        return self._nodes[nid]

    # endregion nodes

    # region edges
    # region add/remove edges
    # endregion add/remove edges
    # endregion edges

    # region lib
    @emit_after()
    def add_shelf(self, shelf: Shelf):
        self.lib.add_shelf(shelf)
        return self.lib

    # endregion lib
    async def await_done(
        self,
    ):
        """await_done waits until all nodes are done"""
        return await run_until_complete(*self.nodes)
