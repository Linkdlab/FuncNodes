from __future__ import annotations
from abc import ABC, ABCMeta
from typing import (
    Callable,
    Type,
    Coroutine,
    Any,
    Dict,
    List,
    TypedDict,
    get_type_hints,
    Optional,
)
import inspect
from exposedfunctionality import assure_exposed_method
from exposedfunctionality.func import ExposedMethodKwargs, ExposedMethodKwargsKeys
from exposedfunctionality.function_parser.types import ReturnType, ExposedFunction
from .node import Node, NodeClassDictsKeys, NodeClassDict, _get_nodeclass_inputs
from .io import NodeInput, NodeOutput
import asyncio
from functools import wraps, partial

from weakref import WeakValueDictionary

try:
    from typing import Unpack
except ImportError:
    from typing_extensions import Unpack


def node_class_maker(
    id: Optional[str] = None,
    func: Callable[..., ReturnType] = None,
    **kwargs: Unpack[NodeClassDict],
) -> Type[Node]:
    if "node_id" not in kwargs:
        if id is None:
            raise ValueError("node_id not set")
        else:
            kwargs["node_id"] = id
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

    kwargs.setdefault("node_name", in_func.ef_funcmeta.get("name", id))
    kwargs.setdefault(
        "description", (in_func.ef_funcmeta.get("docstring") or {}).get("summary", "")
    )
    cls_dict = {"func": _wrapped_func, **kwargs}

    for ip in inputs:
        cls_dict["input_" + ip._name] = ip
    for op in outputs:
        cls_dict["output_" + op._name] = op

    name = "".join(
        x.capitalize()
        for x in in_func.ef_funcmeta.get("name", exfunc.__name__).lower().split("_")
    )
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


class NodeDecoratorKwargs(ExposedMethodKwargs, NodeClassDict, total=False):
    pass


def NodeDecorator(
    id: Optional[str] = None, **kwargs: Unpack[NodeDecoratorKwargs]
) -> Callable[..., Type[Node]]:
    """creates a nodeclass and registers it in the REGISTERED_NODES dict, which runs the function when called"""
    if "node_id" not in kwargs:
        if id is None:
            raise ValueError("node_id not set")
        else:
            kwargs["node_id"] = id
    exposedmethodkwargs: ExposedMethodKwargs = {}
    for v in ExposedMethodKwargsKeys:
        if v in kwargs:
            exposedmethodkwargs[v] = kwargs[v]  # type: ignore

    nodeclasskwargs: NodeClassDict = {}
    for v in NodeClassDictsKeys:
        if v in kwargs:
            # typing requires .get here [] raises a warning despite its checked before
            nodeclasskwargs[v] = kwargs[v]  # type: ignore

    def decorator(func: Callable[..., ReturnType]) -> Type[Node]:

        func = assure_exposed_method(func, **exposedmethodkwargs)
        return node_class_maker(id, func, **nodeclasskwargs)

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


def instance_nodefunction(
    trigger_on_call: Optional[bool] = None, **kwargs: Unpack[NodeDecoratorKwargs]
):
    kwargs.setdefault("default_trigger_on_create", False)

    def decorator(func):
        func._is_instance_nodefunction = True
        func._node_create_params = kwargs
        func._instance_node_specials = {"trigger_on_call": trigger_on_call}
        func._nodeclass = None

        func.triggers = trigger_decorator(func)

        return func

    return decorator


def trigger_decorator(target_func):
    def decorator(func):
        if not hasattr(target_func, "_nodeclass"):
            raise ValueError("trigger can only be used on instance_nodefunctions")

        @wraps(func)
        def func_wrapper(*args, **kwargs):
            res = func(*args, **kwargs)

            for node in target_func._nodeclass._instances.values():
                node.request_trigger()
            return res

        return func_wrapper

    return decorator


def _make_get_node_method(
    nodeclassmixininst: NodeClassMixin, method: Callable, name: str
):
    def _get_node() -> Any:
        nodeclassmixininst.create_nodes()
        return getattr(getattr(nodeclassmixininst, name), "_node")

    setattr(method, "get_node", _get_node)

    def _get_nodes() -> Any:
        nodeclassmixininst.create_nodes()
        return getattr(getattr(nodeclassmixininst, name), "_nodes")

    setattr(method, "get_nodes", _get_nodes)


def _create_node(nodeclassmixininst: NodeClassMixin, method, name):
    node_id = f"{nodeclassmixininst.NODECLASSID}.{nodeclassmixininst.uuid}.{name}"

    mininmethodname = None
    for k, v in nodeclassmixininst.__class__.__dict__.items():
        if v == method:
            mininmethodname = k
            break
    if mininmethodname is None:
        raise ValueError("method not found in class")

    _node_create_params = {
        "id": node_id,
        #        "trigger_on_create": False,
        **getattr(method, "_node_create_params", {}),
    }
    _node_create_params.setdefault("name", name.title())

    # copymethode = partial(method)
    partial_method = partial(method, nodeclassmixininst)

    nodeclass: Type[Node] = NodeDecorator(**_node_create_params)(partial_method)

    # nodeclass should keep track of its instances:

    nodeclass._instances = WeakValueDictionary()

    original__init__ = nodeclass.__init__

    def new__init__(self, *args, **kwargs):
        original__init__(self, *args, **kwargs)
        nodeclass._instances[self.uuid] = self

    nodeclass.__init__ = new__init__

    original__del__ = nodeclass.__del__

    def new__del__(self):
        original__del__(self)
        if self.uuid in nodeclass._instances:
            del nodeclass._instances[self.uuid]

    nodeclass.__del__ = new__del__

    method._nodeclass = nodeclass
    # if the method is called directly on the class, it should also trigger the corresponding nodes
    instance_node_specials = getattr(method, "_instance_node_specials", {})
    trigger_on_call = instance_node_specials.get("trigger_on_call", None)
    if trigger_on_call is None:
        trigger_on_call = len(_get_nodeclass_inputs(nodeclass)) == 0

    if trigger_on_call:

        def new_method(*args, **kwargs):
            res = method(nodeclassmixininst, *args, **kwargs)
            for node in nodeclass._instances.values():
                node.request_trigger()
            return res

        setattr(nodeclassmixininst, mininmethodname, new_method)
    # nodeclass = NodeDecorator(**_node_create_params)(method)

    nodeclassmixininst._node_classes[node_id] = nodeclass

    # def _get_node() -> Any:
    #     return getattr(copymethode, "_node")

    # def _get_nodes() -> Any:
    #     return getattr(copymethode, "_nodes")

    # setattr(copymethode, "get_node", _get_node)
    # setattr(copymethode, "get_nodes", _get_nodes)
    # setattr(copymethode, "_node", node)
    # setattr(copymethode, "_nodes", WeakValueDictionary())
    # setattr(nodeclassmixininst, name, copymethode)


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
