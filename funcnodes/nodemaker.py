from __future__ import annotations
from abc import ABC, ABCMeta
from typing import Callable, Type, Coroutine, Any, Dict, List
import inspect
from exposedfunctionality import assure_exposed_method
from exposedfunctionality.function_parser.types import ReturnType, ExposedFunction
from .node import Node
from .io import NodeInput, NodeOutput
import asyncio
from functools import wraps


def node_class_maker(id: str, func: Callable[..., ReturnType]) -> Type[Node]:
    in_func = assure_exposed_method(func)
    inputs = [
        NodeInput.from_serialized_input(ip)
        for ip in in_func.ef_funcmeta["input_params"]
    ]
    outputs = [
        NodeOutput.from_serialized_output(op)
        for op in in_func.ef_funcmeta["output_params"]
    ]

    if not asyncio.iscoroutinefunction(in_func):
        ofunc = in_func

        @wraps(ofunc)
        async def asyncfunc(*args, **kwargs):
            return ofunc(*args, **kwargs)

    else:
        in_func: ExposedFunction[Coroutine[Any, Any, ReturnType]] = in_func
        asyncfunc = in_func

    exfunc: ExposedFunction[Coroutine[Any, Any, ReturnType]] = asyncfunc

    async def _wrapped_func(self: Node, *args, **kwargs):
        outs = await exfunc(*args, **kwargs)
        if len(outputs) > 1:
            for op, out in zip(outputs, outs):
                self.outputs[op.name].value = out
        elif len(outputs) == 1:
            self.outputs[outputs[0].name].value = outs
        return outs

    cls_dict = {
        "node_id": id,
        "func": _wrapped_func,
        "node_name": in_func.ef_funcmeta.get("name", id),
    }
    if "docstring" in exfunc.ef_funcmeta and exfunc.ef_funcmeta["docstring"]:
        cls_dict["description"] = exfunc.ef_funcmeta["docstring"]["summary"]

    for ip in inputs:
        cls_dict["input_" + ip._name] = ip
    for op in outputs:
        cls_dict["output_" + op._name] = op

    name = "".join(x.capitalize() for x in exfunc.__name__.lower().split("_"))
    if name.endswith("node"):
        name = name[:-4]
    if not name.endswith("Node"):
        name += "Node"
    _Node: Type[Node] = type(
        name,
        (Node,),
        cls_dict,
    )

    return _Node


def NodeDecorator(id: str, **kwargs) -> Callable[..., Type[Node]]:
    """creates a nodeclass and registers it in the REGISTERED_NODES dict, which runs the function when called"""

    def decorator(func: Callable[..., ReturnType]) -> Type[Node]:
        func = assure_exposed_method(func, **kwargs)
        return node_class_maker(id, func)

    return decorator


class NodeClassMixinMeta(ABCMeta):
    def __init__(cls: Type[NodeClassMixin], name, bases, dct):
        super().__init__(name, bases, dct)
        if (
            (not cls.IS_ABSTRACT or "IS_ABSTRACT" not in dct)
            and cls.NODECLASSID is None
            and not inspect.isabstract(cls)
        ):
            raise ValueError(f"NODECLASSID not set for {cls.__name__}")


class NodeClassMixin(ABC, metaclass=NodeClassMixinMeta):
    NODECLASSID: str = None  # type: ignore
    IS_ABSTRACT = True

    @property
    def uuid(self):
        if self._uuid is None:
            raise ValueError("uuid not set")
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        if self._uuid is not None:
            raise ValueError("uuid already set")
        self._uuid = value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_classes: Dict[str, Type[Node]] = {}
        self._uuid = None
        self._nodes_created = False

        for name, method in self.__class__.__dict__.items():
            if hasattr(method, "_is_instance_nodefunction"):
                _make_get_node_method(self, method, name)

    def create_nodes(self):
        if self._nodes_created:
            return
        for name, method in self.__class__.__dict__.items():
            if hasattr(method, "_is_instance_nodefunction"):
                _create_node(self, method, name)

        self._nodes_created = True

    def get_all_nodeclasses(self) -> List[Type[Node]]:
        self.create_nodes()
        return list(self._node_classes.values())

    def get_all_nodes(self) -> List[Node]:
        nodes = []
        for m in [ncls.method for ncls in self.get_all_nodeclasses()]:
            nodes.extend(list(m.nodes.values()))
        return nodes

    def _on_node_event(self, event, **data):
        try:
            src = data["src"]
            cls = self._node_classes[src.node_id]
            cls.method._nodes[src.id] = src
        except (AttributeError, KeyError):
            pass
