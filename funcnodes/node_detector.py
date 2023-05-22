from __future__ import annotations
from typing import List, Callable
from ._typing import (
    LibShelf,
    NodeIdType,
)


def isin_in_shelf(shelf: LibShelf, node_id: NodeIdType) -> bool:
    for node in shelf["nodes"]:
        if node.node_id == node_id:
            return True
    for shelf in shelf["shelves"]:
        res = isin_in_shelf(shelf, node_id)
        if res:
            return True
    return False


def in_np_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.numpy_nodes import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def in_pd_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.pandas_nodes import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def in_progflow_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.progflow import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def in_conversion_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.conversion import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def in_basic_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.basic import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def find_node_id(node_id: NodeIdType):
    for find_func in NODE_SOURCES:
        try:
            res = find_func(node_id)
            if res:
                return res
        except ModuleNotFoundError as e:
            print(e)

    return None


def in_frontend_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.frontend_nodes import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


def in_scipy_nodes(node_id: NodeIdType) -> LibShelf | None:
    from .nodes.scipy_nodes import LIB

    if isin_in_shelf(LIB, node_id):
        return LIB
    return None


NODE_SOURCES: List[Callable[[NodeIdType], LibShelf | None]] = [
    in_np_nodes,
    in_pd_nodes,
    in_conversion_nodes,
    in_progflow_nodes,
    in_basic_nodes,
    in_frontend_nodes,
    in_scipy_nodes,
]
