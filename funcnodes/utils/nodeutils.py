from __future__ import annotations
from typing import Set, Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from ..node import Node


def get_deep_connected_nodeset(
    src: Node, nodeset: Optional[Set[Node]] = None
) -> Set[Node]:
    """
    Recursively collects all the nodes that are connected to the source node, including those
    connected indirectly through other nodes' outputs. This function traverses the graph of nodes
    starting from the source node.

    Args:
        src (Node): The source node from which to start the traversal.
        nodeset (Optional[Set[Node]]): The set of nodes already visited in the traversal,
                                             used to avoid cycles and repeated nodes.

    Returns:
        Set[Node]: A set containing all the connected nodes including the source node.
    """
    # Initialize the nodeset if not provided.
    if nodeset is None:
        nodeset = set()
    # If the source node is already in the set, return the set to avoid infinite recursion.
    if src in nodeset:
        return nodeset

    # Add the source node to the set.
    nodeset.add(src)

    # Iterate through all the outputs of the source node.
    for out in src._outputs:
        # For each output, iterate through its connections.
        for con in out.connections:
            # If the connected node is not already in the set, recurse with the connected node.
            if con.node and con.node not in nodeset:
                get_deep_connected_nodeset(con.node, nodeset)

    # Return the set containing all connected nodes.
    return nodeset


async def run_until_complete(*nodes: Node) -> None:
    """
    Asynchronously runs a loop that checks if the nodes provided are in a trigger state.
    If a node is in a trigger state and requests a trigger, the function will trigger it.
    The loop continues until none of the nodes are in a trigger state.

    Args:
        *nodes (Node): A variable number of Node instances that need to be run until completion.

    Returns:
        None
    """
    # Continue the loop while any node is in a trigger state.
    triggernodes = [node for node in nodes if node.in_trigger]
    while triggernodes:
        # Wait for a short interval to prevent a tight loop that could lock up resources.
        await asyncio.gather(*[n.wait_for_trigger_finish() for n in triggernodes])
        # Iterate through each node.
        for node in nodes:
            # If the node requests a trigger, trigger it.
            node.trigger_if_requested()
        # Get the list of nodes that are in a trigger state.
        triggernodes = [node for node in nodes if node.in_trigger]
