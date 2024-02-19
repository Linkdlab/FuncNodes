from typing import List, Dict, TypedDict, Tuple, Any
from funcnodes import Node, run_until_complete
import json
from uuid import uuid4
from .node import FullNodeJSON, NodeJSON
from .io import NodeInput, NodeOutput
from .lib import FullLibJSON, Library
from .eventmanager import EventEmitterMixin, MessageInArgs
from .utils.serialization import JSONEncoder, JSONDecoder


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
            "nodes": [node.full_serialize() for name, node in self._nodes.items()],
            "prop": self._properties,
            "lib": self.lib.full_serialize(),
            "edges": self.serialize_edges(),
        }

    def deserialize_nodes(self, data: List[NodeJSON]) -> Dict[str, Node]:
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
        ret = {}
        for node in data:
            node_cls = self.lib.get_node_by_id(node["node_id"])
            if node_cls is None:
                raise ValueError(
                    f"node with node_id '{node['node_id']}' not found in lib"
                )
            node_instance = node_cls()
            node_instance.deserialize(node)
            ret[node_instance.uuid] = node_instance
        self._nodes = ret
        return ret

    def serialize_nodes(self) -> List[NodeJSON]:
        """serialize_nodes serializes the nodes in the nodespace

        Returns
        -------
        List[NodeJSON]
            the serialized nodes
        """
        ret = []
        for name, node in self._nodes.items():
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
        self._properties = data.get("prop", {})
        self.deserialize_nodes(data.get("nodes", []))

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
        node_ser = node.serialize()
        msg = MessageInArgs(node=node_ser)
        self.emit("node_added", msg)
        return node

    def remove_node_instance(self, node: Node):
        if node.uuid not in self._nodes:
            raise ValueError(f"node with uuid '{node.uuid}' not found in nodespace")

        node = self._nodes.pop(node.uuid)

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
        return node

    def add_node_by_id(self, id: str, **kwargs):
        # find node in lib
        node_cls = self.lib.get_node_by_id(id)
        if node_cls is None:
            raise ValueError(f"node with id '{id}' not found in lib")

        node = node_cls(**kwargs)
        return self.add_node_instance(node)

    def remove_node_by_id(self, id: str):
        if id not in self._nodes:
            raise ValueError(f"node with id '{id}' not found in nodespace")
        return self.remove_node_instance(self._nodes[id])

    # endregion add/remove nodes

    def get_node_by_id(self, id: str) -> Node:
        if id not in self._nodes:
            raise ValueError(f"node with id '{id}' not found in nodespace")
        return self._nodes[id]

    # endregion nodes
    async def await_done(
        self,
    ):
        """await_done waits until all nodes are done"""
        return await run_until_complete(*self.nodes)
