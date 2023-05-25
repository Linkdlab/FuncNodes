import numpy as np
from funcnodes.node_creator import func_to_node, FuncNodeFunctionParam, OutputParam
from funcnodes.nodespace import LibShelf
from .types import NdArrayType

# for n in dir(np.random):
#    v = getattr(np.random, n)
#    print(n, v)
RandomNode = func_to_node(
    np.random.random_sample,
    node_id="np.random.random_sample",
    input_params=[
        FuncNodeFunctionParam(name="size", annotation=int, positional=True, default=1)
    ],
    output_params=[OutputParam(name="out", annotation=NdArrayType.typeclass)],
)

# random               Uniformly distributed floats over ``[0, 1)``
# bytes                Uniformly distributed random bytes.
# permutation          Randomly permute a sequence / generate a random sequence.
# shuffle              Randomly permute a sequence in place.
# choice               Random sample from 1-D array.

UTILITY_NODES = {
    "RandomNode": RandomNode,
}

RANDOM_NODES = {**UTILITY_NODES}

LIB = LibShelf(
    name="random",
    nodes=[],
    shelves=[
        LibShelf(
            name="sampling",
            nodes=list(UTILITY_NODES.values()),
            shelves=[],
        )
    ],
)
