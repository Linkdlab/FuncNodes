from __future__ import annotations
from typing import List, TypedDict, Dict, Type, Tuple, Set
from funcnodes.node import Node, SerializedNodeClass


class NodeClassNotFoundError(Exception):
    pass


class Shelf(TypedDict):
    nodes: Dict[str, Type[Node]]
    subshelves: List[Shelf]
    name: str
    description: str


class SerializedShelf(TypedDict):
    nodes: List[SerializedNodeClass]
    subshelves: List[SerializedShelf]
    name: str
    description: str


def serialize_shelfe(shelve: Shelf) -> SerializedShelf:
    """
    Serializes a shelf object into a dictionary.
    """
    return {
        "nodes": [
            node.serialize_cls() for node in set(shelve["nodes"].values())
        ],  # unique nodes, necessary since somtimes nodes are added multiple times if they have aliases
        "subshelves": [serialize_shelfe(shelf) for shelf in shelve["subshelves"]],
        "name": shelve["name"],
        "description": shelve["description"],
    }


def update_nodes_in_shelf(shelf: Shelf, nodes: List[Type[Node]]):
    """
    Adds nodes to a shelf
    """
    for node in nodes:
        shelf["nodes"][node.node_id] = node


def deep_find_node(shelf: Shelf, nodeid: str, all=True) -> List[List[str]]:
    paths = []
    if nodeid in shelf["nodes"]:
        paths.append([shelf["name"]])
        if not all:
            return paths

    for subshelf in shelf["subshelves"]:
        path = deep_find_node(subshelf, nodeid)
        if len(path) > 0:
            for p in path:
                p.insert(0, shelf["name"])
            paths.extend(path)
            if not all:
                break
    return paths


class Library:
    def __init__(self) -> None:
        self._shelves: Dict[str, Shelf] = {}
        self._dependencies: Dict[str, Set[str]] = {
            "modules": set(),
        }

    @property
    def shelves(self) -> List[Shelf]:
        return list(self._shelves.values())

    def add_dependency(self, module: str):
        self._dependencies["modules"].add(module)

    def get_dependencies(self) -> Dict[str, List[str]]:
        return {k: list(v) for k, v in self._dependencies.items()}

    def add_shelf(self, shelf: Shelf):
        if shelf["name"] in self._shelves and self._shelves[shelf["name"]] != shelf:
            raise ValueError(f"Shelf with name {shelf['name']} already exists")
        self._shelves[shelf["name"]] = shelf

    def get_shelf(self, name: str) -> Shelf:
        return self._shelves[name]

    def full_serialize(self) -> FullLibJSON:
        return {"shelves": [serialize_shelfe(shelf) for shelf in self.shelves]}

    def add_nodes(
        self,
        nodes: List[Type[Node]],
        shelf: str | List[str],
    ):
        if isinstance(shelf, str):
            shelf = [shelf]

        subshelfes: Dict[str, Shelf] = self._shelves
        if len(shelf) == 0:
            raise ValueError("shelf must not be empty")
        current_shelf = None
        for _shelf in shelf:
            if _shelf not in subshelfes:
                subshelfes[_shelf] = Shelf(
                    nodes={}, subshelves=[], name=_shelf, description=""
                )
            current_shelf = subshelfes[_shelf]
            subshelfes = {s["name"]: s for s in subshelfes[_shelf]["subshelves"]}
        if current_shelf is None:
            raise ValueError("shelf must not be empty")
        update_nodes_in_shelf(current_shelf, nodes)

    def add_node(self, node: Type[Node], shelf: str | List[str]):
        self.add_nodes([node], shelf)

    def get_shelf_from_path(self, path: List[str]) -> Shelf:
        subshelfes: Dict[str, Shelf] = self._shelves
        for _shelf in path[:-1]:
            if _shelf not in subshelfes:
                raise ValueError(f"shelf {_shelf} does not exist")
            subshelfes = {s["name"]: s for s in subshelfes[_shelf]["subshelves"]}
        return subshelfes[path[-1]]

    def find_nodeid(self, nodeid: str, all=True) -> List[List[str]]:
        paths = []
        for shelf in self.shelves:
            path = deep_find_node(shelf, nodeid, all=all)
            if len(path) > 0:
                paths.extend(path)
                if not all:
                    break
        return paths

    def has_node_id(self, nodeid: str) -> bool:
        return len(self.find_nodeid(nodeid, all=False)) > 0

    def find_nodeclass(self, node: Type[Node], all=True) -> List[List[str]]:
        return self.find_nodeid(node.node_id, all=all)

    def remove_nodeclass(self, node: Type[Node]):
        paths = self.find_nodeclass(node)
        for path in paths:
            shelf = self.get_shelf_from_path(path)
            del shelf["nodes"][node.node_id]

    def remove_nodeclasses(self, nodes: List[Type[Node]]):
        for node in nodes:
            self.remove_nodeclass(node)

    def get_node_by_id(self, nodeid: str) -> Type[Node]:
        paths = self.find_nodeid(nodeid, all=False)
        if len(paths) == 0:
            raise NodeClassNotFoundError(f"Node with id '{nodeid}' not found")

        print(paths)
        shelf = self.get_shelf_from_path(paths[0])
        return shelf["nodes"][nodeid]


class FullLibJSON(TypedDict):
    """
    FullLibJSON for a full serilization including temporary properties
    """

    shelves: List[SerializedShelf]
