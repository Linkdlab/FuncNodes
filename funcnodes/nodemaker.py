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
from .node import (
    Node,
    NodeClassDictsKeys,
    NodeClassDict,
    _get_nodeclass_inputs,
    NodeMeta,
)
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
    superclass: Type[Node] = Node,
    **kwargs: Unpack[NodeClassDict],
) -> Type[Node]:
    if superclass != Node and not issubclass(superclass, Node):
        raise ValueError("superclass must be a subclass of Node")

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
        (superclass,),
        cls_dict,
    )

    return _Node


class NodeDecoratorKwargs(ExposedMethodKwargs, NodeClassDict, total=False):
    superclass: Optional[Type[Node]]


def NodeDecorator(
    id: Optional[str] = None, **kwargs: Unpack[NodeDecoratorKwargs]
) -> Callable[..., Type[Node]]:
    """Decorator to create a Node class from a function."""

    # Ensure node_id is set
    if "node_id" not in kwargs:
        if id is None:
            raise ValueError("node_id not set")
        else:
            kwargs["node_id"] = id

    def decorator(func: Callable[..., ReturnType]) -> Type[Node]:
        # Prepare function and node class arguments
        exposed_method_kwargs: ExposedMethodKwargs = {
            v: kwargs[v] for v in ExposedMethodKwargsKeys if v in kwargs  # type: ignore
        }
        node_class_kwargs: NodeClassDict = {
            v: kwargs[v] for v in NodeClassDictsKeys if v in kwargs  # type: ignore
        }

        # Assure the method is exposed for node functionality
        func = assure_exposed_method(func, **exposed_method_kwargs)
        # Create the node class
        return node_class_maker(
            id, func, superclass=kwargs.get("superclass", Node), **node_class_kwargs
        )

    return decorator


def instance_nodefunction(
    trigger_on_call: Optional[bool] = None, **kwargs: Unpack[NodeDecoratorKwargs]
):
    kwargs.setdefault("default_trigger_on_create", False)

    def decorator(func):
        func._is_instance_nodefunction = True
        func._node_create_params = kwargs
        func._instance_node_specials = {"trigger_on_call": trigger_on_call}

        func.triggers = trigger_decorator(func)

        return func

    return decorator


def trigger_decorator(target_func):
    def decorator(func):
        if not hasattr(target_func, "_is_instance_nodefunction"):
            raise ValueError("trigger can only be used on instance_nodefunctions")

        @wraps(func)
        def func_wrapper(instance: NodeClassMixin, *args, **kwargs):
            res = func(instance, *args, **kwargs)
            nodeclass = instance._node_classes[target_func.__name__]

            for node in nodeclass._instances.values():
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


class NodeClassNodeMeta(NodeMeta):
    def __new__(cls, name, bases, dct):
        new_cls: Type[NodeClassNode] = super().__new__(cls, name, bases, dct)  # type: ignore
        new_cls._instances = WeakValueDictionary()
        return new_cls


class NodeClassNode(Node, ABC, metaclass=NodeClassNodeMeta):
    _instances = WeakValueDictionary()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__class__._instances[self.uuid] = self

    def __del__(self):
        if self.uuid in self.__class__._instances:
            del self.__class__._instances[self.uuid]
        super().__del__()


def _create_node(nodeclassmixininst: NodeClassMixin, method, method_name):
    # first we define a unique id for the node
    node_id = (
        f"{nodeclassmixininst.NODECLASSID}.{nodeclassmixininst.uuid}.{method_name}"
    )

    # hecking if the method is actually in the class
    if method_name not in nodeclassmixininst.__class__.__dict__:
        raise ValueError("method not found in class")

    if nodeclassmixininst.__class__.__dict__[method_name] != method:
        raise ValueError(
            "class method is not the same as the method passed to the function."
        )

    # then we create the node class
    _node_create_params = {
        "id": node_id,
        #        "trigger_on_create": False,
        **getattr(method, "_node_create_params", {}),
    }
    _node_create_params["superclass"] = NodeClassNode
    _node_create_params.setdefault(
        "name", method_name.title()
    )  # default name is the method name

    # create a partial method that is bound to the nodeclassmixininst
    partial_method = partial(method, nodeclassmixininst)

    # create the node class
    nodeclass: Type[Node] = NodeDecorator(**_node_create_params)(partial_method)

    # nodeclass should keep track of its instances:

    # add instances to the class

    nodeclassmixininst._node_classes[method_name] = nodeclass
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

        setattr(nodeclassmixininst, method_name, new_method)
    # nodeclass = NodeDecorator(**_node_create_params)(method)

    # def _get_node() -> Any:
    #     return getattr(copymethode, "_node")

    # def _get_nodes() -> Any:
    #     return getattr(copymethode, "_nodes")

    # setattr(copymethode, "get_node", _get_node)
    # setattr(copymethode, "get_nodes", _get_nodes)
    # setattr(copymethode, "_node", node)
    # setattr(copymethode, "_nodes", WeakValueDictionary())
    # setattr(nodeclassmixininst, name, copymethode)


class NodeClassMixinMeta(ABCMeta):
    def __init__(cls: Type[NodeClassMixin], name, bases, dct):
        super().__init__(name, bases, dct)
        # Abstract classes are exempt from the following checks.

        if inspect.isabstract(cls):
            return

        # Check for the IS_ABSTRACT flag in the class dictionary; defaults to False if not present.
        is_abstract = dct.get("IS_ABSTRACT", False) and cls.IS_ABSTRACT

        # Check if NODECLASSID is defined unless the class is explicitly marked as abstract.
        if not is_abstract and cls.NODECLASSID is None:
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
        self._node_classes: Dict[str, Type[NodeClassNode]] = (
            {}
        )  # maps method names to node classes
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
