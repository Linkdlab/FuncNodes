"""
helper modul for creating nodes from functions
"""
from __future__ import annotations
import json
from typing import List, Type, Any, Callable, Dict, get_type_hints
import sys
from functools import partial
from abc import ABCMeta
from weakref import WeakValueDictionary

if sys.version_info < (3, 11):
    from typing_extensions import Required, TypedDict
else:
    from typing import Required, TypedDict

import asyncio
import inspect
import warnings

from ..io import (
    NodeInput,
    NodeOutput,
    IOProperties,
)
from ..iotypes import IOType

from ..node import Node, NodeIdType


class FunctionBasedNode(Node):
    """Base class for nodes that are created from functions"""

    node_id = "_func_to_node_base"
    func: Callable[..., Any]

    async def on_trigger(self):
        raise ValueError("this. on_trigger should not be called")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


func_to_node_base = FunctionBasedNode()


class FuncNodeError(NameError):
    """Exception for FuncNode"""


class FuncNodeReservedNameError(FuncNodeError):
    """Exception for FuncNode if an argument would overwrite a reserved name"""


class FuncNodeUnserializableDefaultError(FuncNodeError):
    """Exception for FuncNode if a default value is not serializable"""


class FuncNodeWarning(UserWarning):
    """Warning for FuncNode"""


class FuncNodeFunctionParam(TypedDict, total=False):
    """Type definition for a function parameter"""

    name: Required[str]
    default: Any
    annotation: Required[Any]
    positional: Required[bool]


class OutputParam(TypedDict):
    """Type definition for an output parameter"""

    name: str
    annotation: Any


def func_to_node(
    func: Callable,
    node_id: NodeIdType | None = None,
    input_params: List[FuncNodeFunctionParam] | None = None,
    output_params: List[OutputParam] | None = None,
    nodeclass_name: str | None = None,
    requirements: list | None = None,
    baseclass: Type[FunctionBasedNode] = FunctionBasedNode,
    node_initialization_params: dict | None = None,
    trigger_on_create: bool | None = None,
) -> Type[FunctionBasedNode]:
    """Converts a function to a nodeclass

    Parameters
    ----------
    func : Callable
        The function to be converted
    *args : Any
        The args to be passed to the function
    **kwargs : Any
        The kwargs to be passed to the function

    Returns
    -------
    Node
        The nodeclass that represents the function
    """
    if node_id is None:
        node_id = f"func_{func.__module__}.{func.__name__}"

    # check if function is async
    if asyncio.iscoroutinefunction(func):
        _func = func
    else:
        # if not convert to async
        async def _func(*args, **kwargs):
            return func(*args, **kwargs)

    inputs = {}
    input_names = []
    # craete inputs from function signature
    if requirements is None:
        requirements = []
    if input_params is None:
        input_params = []
        param_order = []
        sig = inspect.signature(func)
        for i, p in sig.parameters.items():
            param_order.append(i)
            param_dict: FuncNodeFunctionParam = {
                "name": i,
                "default": p.default,
                "annotation": p.annotation,
                "positional": p.kind == p.POSITIONAL_OR_KEYWORD,
            }

            if param_dict["annotation"] is p.empty:
                warnings.warn(
                    f"input {i} has no type annotation, using Any as type",
                    FuncNodeWarning,
                )
                param_dict["annotation"] = Any

            if param_dict["default"] is not p.empty:
                try:
                    json.dumps(param_dict["default"])
                except TypeError as exe:
                    raise FuncNodeUnserializableDefaultError(
                        f"input {i} has unserializable default value '{param_dict['default']}'"
                    ) from exe
            else:
                del param_dict["default"]

            input_params.append(param_dict)
    else:
        param_order = [p["name"] for p in input_params]

    positionals = []

    for i, p in enumerate(input_params):
        io_type = IOType.get_type(p["annotation"])
        input_dict = IOProperties(id=p["name"], type=io_type.typestring)

        if "default" in p:
            input_dict["default_value"] = p["default"]
        else:
            input_dict["required"] = True

        if p["positional"]:
            positionals.append(input_dict["id"])
        inputs[input_dict["id"]] = NodeInput(input_dict)
        input_names.append(input_dict["id"])

    for i in input_names:
        if hasattr(func_to_node_base, i):
            raise FuncNodeReservedNameError(f"input {i} is reserved")

    if output_params is None:
        try:
            _f = func
            if isinstance(_f, partial):
                while isinstance(_f, partial):
                    _f = _f.func
            th = get_type_hints(_f)
            if "return" in th:
                # chek if return type is None Type
                nt = type(None)
                if th["return"] == nt:
                    output_params = []
                else:
                    output_params = [{"name": "out", "annotation": th["return"]}]
        except TypeError:
            pass

    if output_params is None:
        output_params = [{"name": "out", "annotation": Any}]

    output_names = []
    node_outputs = {}
    for o in output_params:
        io_type = IOType.get_type(o["annotation"])

        output_dict = IOProperties(id=o["name"], type=io_type.typestring)
        node_outputs[output_dict["id"]] = NodeOutput(output_dict)
        output_names.append(output_dict["id"])

    for i in output_names:
        if hasattr(func_to_node_base, i):
            raise FuncNodeReservedNameError(f"output {i} is reserved")
        if i in inputs:
            raise FuncNodeReservedNameError(f"output {i} is already an input")

    async def on_trigger(self: Node):
        input_values = {}
        args = []
        for input_name in input_names:
            if input_name in positionals:
                args.append(self.io[input_name].value)
            else:
                input_values[input_name] = self.io[input_name].value
        v = await _func(*args, **input_values)
        if len(output_names) == 1:
            self.io[output_names[0]].value = v
        else:
            for i, o in enumerate(output_names):
                self.io[o].value = v[i]
        return True

    if nodeclass_name is None:
        nodeclass_name = "".join(x.title() for x in func.__name__.split("_")) + "Node"

    if node_initialization_params is None:
        node_initialization_params = {}

    def _int(self, *args, **kwargs):
        return super(self.__class__, self).__init__(
            *args, **{**node_initialization_params, **kwargs}
        )

    classdict = {
        "requirements": requirements,
        "node_id": node_id,
        "on_trigger": on_trigger,
        "func": func,
        "trigger_on_create": trigger_on_create
        if trigger_on_create is not None
        else Node.trigger_on_create,
        "__init__": _int,
        **inputs,
        **node_outputs,
    }

    NodeClass: Type[baseclass] = type(nodeclass_name, (baseclass,), classdict)
    return NodeClass


def func_to_node_decorator(
    node_id: NodeIdType | None = None,
) -> Callable[[Callable[..., Any]], Type[FunctionBasedNode]]:
    """Converts a function to a nodeclass

    Parameters
    ----------
    func : Callable
        The function to be converted
    *args : Any
        The args to be passed to the function
    **kwargs : Any
        The kwargs to be passed to the function

    Returns
    -------
    Node
        The nodeclass that represents the function
    """

    def wrapper(func):
        return func_to_node(func, node_id=node_id)

    return wrapper


def intialize_class_nodes(cls):
    for name, method in cls.__dict__.items():
        if hasattr(method, "_is_node_function"):
            node_id = f"{cls.__name__}.{name}"
            node = func_to_node(method, node_id=node_id)
            setattr(cls, name, node)
    return cls


def _make_get_node_method(
    nodeclassmixininst: NodeClassMixin, method: Callable, name: str
):
    def _get_node() -> Any:
        nodeclassmixininst.create_nodes()
        return getattr(getattr(nodeclassmixininst, name), "node")

    setattr(method, "get_node", _get_node)


def _create_node(nodeclassmixininst: NodeClassMixin, method, name):
    node_id = f"{nodeclassmixininst.NODECLASSID}.{nodeclassmixininst.uuid}.{name}"

    copymethode = partial(method)
    partial_method = partial(copymethode, nodeclassmixininst)

    _node_create_params = {
        "node_id": node_id,
        "trigger_on_create": False,
        "nodeclass_name": f"{nodeclassmixininst.NODECLASSID}.{nodeclassmixininst.uuid}.{name.title()}Node",
        **getattr(method, "_node_create_params", {}),
    }
    _node_create_params["requirements"] = _node_create_params.get(
        "requirements", []
    ) + [
        {
            "type": "nodeclass",
            "class": nodeclassmixininst.NODECLASSID,
            "id": nodeclassmixininst.uuid,
        }
    ]

    _node_create_params.setdefault("node_initialization_params", {}).setdefault(
        "default_listener", {}
    ).setdefault("*", []).append(nodeclassmixininst._on_node_event)

    node = func_to_node(partial_method, **_node_create_params)
    nodeclassmixininst._node_classes[node_id] = node

    def _get_node() -> Any:
        return getattr(copymethode, "node")

    setattr(node, "method", copymethode)
    setattr(copymethode, "get_node", _get_node)
    setattr(copymethode, "node", node)
    setattr(copymethode, "nodes", WeakValueDictionary())
    setattr(nodeclassmixininst, name, copymethode)


class NodeClassMixinMeta(ABCMeta):
    def __init__(cls: Type[NodeClassMixin], name, bases, dct):
        super().__init__(name, bases, dct)
        if (
            (not cls.IS_ABSTRACT or "IS_ABSTRACT" not in dct)
            and cls.NODECLASSID is None
            and not inspect.isabstract(cls)
        ):
            raise ValueError(f"NODECLASSID not set for {cls.__name__}")


class NodeClassMixin(metaclass=NodeClassMixinMeta):
    NODECLASSID = None
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
        self._node_classes: Dict[NodeIdType, Type[Node]] = {}
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
            cls.method.nodes[src.id] = src
        except (AttributeError, KeyError):
            pass


def instance_nodefunction(**kwargs):
    def decorator(func):
        func._is_instance_nodefunction = True
        func._node_create_params = kwargs
        return func

    return decorator
