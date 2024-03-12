from __future__ import annotations
from typing import List, TypedDict, Dict, Type, Tuple, Set
from funcnodes.node import Node, SerializedNodeClass


class NodeClassNotFoundError(Exception):
    pass


class Shelf(TypedDict):
    nodes: List[Type[Node]]
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
            node.serialize_cls() for node in shelve["nodes"]
        ],  # unique nodes, necessary since somtimes nodes are added multiple times if they have aliases
        "subshelves": [serialize_shelfe(shelf) for shelf in shelve["subshelves"]],
        "name": shelve["name"],
        "description": shelve["description"],
    }


def get_node_in_shelf(shelf: Shelf, nodeid: str) -> Tuple[int, Type[Node]]:
    """
    Returns the index and the node with the given id
    """
    for i, node in enumerate(shelf["nodes"]):
        if node.node_id == nodeid:
            return i, node
    raise ValueError(f"Node with id {nodeid} not found")


def update_nodes_in_shelf(shelf: Shelf, nodes: List[Type[Node]]):
    """
    Adds nodes to a shelf
    """
    for node in nodes:
        try:
            i, _ = get_node_in_shelf(shelf, node.node_id)
            shelf["nodes"][i] = node
        except ValueError:
            shelf["nodes"].append(node)


def deep_find_node(shelf: Shelf, nodeid: str, all=True) -> List[List[str]]:
    paths = []
    try:
        i, node = get_node_in_shelf(shelf, nodeid)
        paths.append([shelf["name"]])
        if not all:
            return paths
    except ValueError:
        pass

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
        self._shelves: List[Shelf] = []
        self._dependencies: Dict[str, Set[str]] = {
            "modules": set(),
        }

    @property
    def shelves(self) -> List[Shelf]:
        return list(self._shelves)

    def add_dependency(self, module: str):
        self._dependencies["modules"].add(module)

    def get_dependencies(self) -> Dict[str, List[str]]:
        return {k: list(v) for k, v in self._dependencies.items()}

    def add_shelf(self, shelf: Shelf):
        shelf_dict = {s["name"]: s for s in self._shelves}
        if shelf["name"] in shelf_dict and shelf_dict[shelf["name"]] != shelf:
            raise ValueError(f"Shelf with name {shelf['name']} already exists")
        self._shelves.append(shelf)
        return shelf

    def add_shelf_recursively(self, path: List[str]):
        subshelfes: List[Shelf] = self._shelves
        current_shelf = None
        for _shelf in path:
            if _shelf not in [subshelfes["name"] for subshelfes in subshelfes]:
                current_shelf = Shelf(
                    nodes=[], subshelves=[], name=_shelf, description=""
                )
                subshelfes.append(current_shelf)
            else:
                for subshelf in subshelfes:
                    if subshelf["name"] == _shelf:
                        current_shelf = subshelf
                        break
            if current_shelf is None:
                raise ValueError("shelf must not be empty")
            subshelfes = current_shelf["subshelves"]
        if current_shelf is None:
            raise ValueError("shelf must not be empty")
        return current_shelf

    def get_shelf(self, name: str) -> Shelf:
        for shelf in self._shelves:
            if shelf["name"] == name:
                return shelf
        raise ValueError(f"Shelf with name {name} not found")

    def full_serialize(self) -> FullLibJSON:
        return {"shelves": [serialize_shelfe(shelf) for shelf in self.shelves]}

    def _repr_json_(self) -> FullLibJSON:
        return self.full_serialize()

    def add_nodes(
        self,
        nodes: List[Type[Node]],
        shelf: str | List[str],
    ):

        if isinstance(shelf, str):
            shelf = [shelf]

        if len(shelf) == 0:
            raise ValueError("shelf must not be empty")

        current_shelf = self.add_shelf_recursively(shelf)
        update_nodes_in_shelf(current_shelf, nodes)

    def add_node(self, node: Type[Node], shelf: str | List[str]):
        self.add_nodes([node], shelf)

    def get_shelf_from_path(self, path: List[str]) -> Shelf:
        subshelfes: List[Shelf] = self._shelves
        current_shelf = None
        for _shelf in path:
            new_subshelfes = None
            for subshelf in subshelfes:
                if subshelf["name"] == _shelf:
                    new_subshelfes = subshelf["subshelves"]
                    current_shelf = subshelf
                    break
            if new_subshelfes is None:
                raise ValueError(f"shelf {_shelf} does not exist")
            subshelfes = new_subshelfes
        if current_shelf is None:
            raise ValueError("shelf must not be empty")
        return current_shelf

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
            i, _ = get_node_in_shelf(shelf, node.node_id)
            shelf["nodes"].pop(i)

    def remove_nodeclasses(self, nodes: List[Type[Node]]):
        for node in nodes:
            self.remove_nodeclass(node)

    def get_node_by_id(self, nodeid: str) -> Type[Node]:
        paths = self.find_nodeid(nodeid, all=False)

        if len(paths) == 0:
            raise NodeClassNotFoundError(f"Node with id '{nodeid}' not found")

        shelf = self.get_shelf_from_path(paths[0])

        return get_node_in_shelf(shelf, nodeid)[1]


class FullLibJSON(TypedDict):
    """
    FullLibJSON for a full serilization including temporary properties
    """

    shelves: List[SerializedShelf]
