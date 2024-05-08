from __future__ import annotations
from abc import ABC, ABCMeta
from typing import (
    Callable,
    Type,
    Coroutine,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
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
    """
    Creates a node class from a function.

    Args:
      id (str, optional): The id of the node. Defaults to None.
      func (Callable[..., ReturnType], optional): The function to be wrapped. Defaults to None.
      superclass (Type[Node], optional): The superclass of the node. Defaults to Node.
      **kwargs (Unpack[NodeClassDict]): Keyword arguments for the node class.

    Returns:
      Type[Node]: The created node class.

    Raises:
      ValueError: If the superclass is not a subclass of Node.
      ValueError: If the node_id is not set.
    """
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
            """
            A wrapper for the exposed function that makes it an asynchronous function.
            """
            return ofunc(*args, **kwargs)

    else:
        in_func: ExposedFunction[Coroutine[Any, Any, ReturnType]] = in_func
        asyncfunc = in_func

    exfunc: ExposedFunction[Coroutine[Any, Any, ReturnType]] = asyncfunc

    @wraps(asyncfunc)
    async def _wrapped_func(self: Node, *args, **kwargs):
        """
        A wrapper for the exposed function that sets the output values of the node.
        """
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
    try:
        name = "".join(
            x.capitalize()
            for x in in_func.ef_funcmeta.get("name", in_func.__name__)
            .lower()
            .split("_")
        )
    except AttributeError:
        raise
    if name.endswith("node"):
        name = name[:-4]
    if not name.endswith("Node"):
        name += "Node"

    if "__doc__" not in cls_dict:
        cls_dict["__doc__"] = in_func.__doc__

    cls_dict["__module__"] = in_func.__module__

    _Node: Type[Node] = type(
        name,
        (superclass,),
        cls_dict,
    )

    return _Node


class NodeDecoratorKwargs(ExposedMethodKwargs, NodeClassDict, total=False):
    """
    Keyword arguments for the node_class_maker function.
    """

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
        """
        Decorator for creating a Node class from a function.
        """
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
    """
    Decorator for creating instance node functions.

    Args:
      trigger_on_call (bool, optional): Whether to trigger the node when the
        underlying NodeClassMixin-function is called.
        If None, the node will be triggered if it has no inputs.
        Defaults to None.
      **kwargs (Unpack[NodeDecoratorKwargs]): Keyword arguments for the decorator.

    Returns:
      Callable: The decorated function.

    Raises:
      ValueError: If the function is not an instance_nodefunction.
    """
    kwargs.setdefault("default_trigger_on_create", False)

    def decorator(func):
        """
        Inner decorator for instance_nodefunction.
        """
        func._is_instance_nodefunction = True
        func._node_create_params = kwargs
        func._instance_node_specials = {"trigger_on_call": trigger_on_call}

        func.triggers = trigger_decorator(func)
        func.nodes = lambda self: self.get_nodes(func.__name__)
        func.nodeclass = lambda self: self.get_nodeclass(func.__name__)

        return func

    return decorator


def trigger_decorator(target_func):
    """
    A decorator that triggers the corresponding nodes when the function is called.

    Args:
      target_func: A function wrapped in instance_nodefunction.

    Returns:
      Callable: The decorated function.

    Raises:
      ValueError: If the function is not an instance_nodefunction.

    Examples:
      >>> class MyNodeClass(NodeClassMixin):
      >>>   NODECLASSID = "my_node_class"
      >>>
      >>>   @instance_nodefunction
      >>>   def add(self, a, b):
      >>>     return a + b
      >>>
      >>>   @add.triggers
      >>>   def eval(self, a, b):
      >>>     # calling this function will trigger the add nodes for this instance
    """

    def decorator(func):
        """
        Inner decorator for trigger_decorator.
        """
        if not hasattr(target_func, "_is_instance_nodefunction"):
            raise ValueError("trigger can only be used on instance_nodefunctions")

        @wraps(func)
        def func_wrapper(instance: NodeClassMixin, *args, **kwargs):
            """
            Wraps a function to handle callings
            """
            res = func(instance, *args, **kwargs)
            for node in instance.get_nodes(target_func.__name__):
                node.request_trigger()
            return res

        return func_wrapper

    return decorator


def _make_get_node_method(
    nodeclassmixininst: NodeClassMixin, method: Callable, name: str
):
    """
    Creates a method for getting the node(s) for a NodeClassMixin method.

    Args:
      nodeclassmixininst (NodeClassMixin): The instance of the node class.
      method (Callable): The method to be decorated.
      name (str): The name of the method.
    """

    def _get_node() -> Any:
        """
        Gets the node.

        Returns:
          Any: The node.
        """
        nodeclassmixininst.create_nodes()
        return getattr(getattr(nodeclassmixininst, name), "_node")

    setattr(method, "get_node", _get_node)

    def _get_nodes() -> Any:
        """
        Gets the nodes.

        Returns:
          Any: The nodes.
        """
        nodeclassmixininst.create_nodes()
        return getattr(getattr(nodeclassmixininst, name), "_nodes")

    setattr(method, "get_nodes", _get_nodes)


class NodeClassNodeMeta(NodeMeta):
    """
    Metaclass for the NodeClassNode class.
    """

    def __new__(cls, name, bases, dct):
        """
        Creates a new NodeClassNode class.

        Args:
          cls (NodeClassNodeMeta): The class to be created.
          name (str): The name of the class.
          bases: The base classes.
          dct: The class dictionary.

        Returns:
          Type[NodeClassNode]: The new class.
        """
        new_cls: Type[NodeClassNode] = super().__new__(cls, name, bases, dct)  # type: ignore
        new_cls._instances = WeakValueDictionary()
        return new_cls


class NodeClassNode(Node, ABC, metaclass=NodeClassNodeMeta):
    """
    Special Node-subclass for NodeClassMixin instances,
    that keeps track of its instances.

    Attributes:
      _instances (WeakValueDictionary): A dictionary of all instances of the node class.
    """

    _instances: WeakValueDictionary[str, NodeClassNode] = WeakValueDictionary()

    def __init__(self, *args, **kwargs):
        """
        Initializes a new instance of the NodeClassNode class.
        """
        super().__init__(*args, **kwargs)
        self.__class__._instances[self.uuid] = self

    def __del__(self):
        """
        Deletes the NodeClassNode instance.
        Side Effects:
          De
        """
        if self.uuid in self.__class__._instances:
            # delete the instance from the class reference
            del self.__class__._instances[self.uuid]
        super().__del__()


def _create_node(nodeclassmixininst: NodeClassMixin, method, method_name):
    """
    Creates a new node for a NodeClassMixin method.

    Args:
      nodeclassmixininst (NodeClassMixin): The NodeClassMixin instance.
      method (Callable): The method to be bound to the node class.
      method_name (str): The name of the method.

    Returns:
      None

    Side Effects:
      Adds the node class to the _node_classes dictionary.
    """
    # first we define a unique id for the node
    node_id = (
        f"{nodeclassmixininst.NODECLASSID}.{nodeclassmixininst.uuid}.{method_name}"
    )

    # hecking if the method is actually in the class
    if getattr(nodeclassmixininst, method_name) is None:
        raise ValueError("method not found in class")

    if (
        getattr(nodeclassmixininst, method_name).__func__ != method
    ):  # __func__  is the unbound method
        raise ValueError(
            f"class method is not the same as the method passed to the function. {getattr(nodeclassmixininst, method_name)}, {method}"
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
    partial_method = wraps(method)(partial(method, nodeclassmixininst))

    # create the node class
    nodeclass: Type[Node] = NodeDecorator(**_node_create_params)(partial_method)

    if not issubclass(nodeclass, NodeClassNode):
        raise ValueError("node class is not a subclass of NodeClassNode")

    # nodeclass should keep track of its instances:

    # add instances to the class

    nodeclassmixininst._node_classes[method_name] = nodeclass
    # if the method is called directly on the class, it should also trigger the corresponding nodes
    instance_node_specials = getattr(method, "_instance_node_specials", {})
    trigger_on_call = instance_node_specials.get("trigger_on_call", None)
    if trigger_on_call is None:
        trigger_on_call = len(_get_nodeclass_inputs(nodeclass)) == 0

    if trigger_on_call:

        @wraps(method)
        def _trigger_on_call_wrapper(*args, **kwargs):
            """
            A wrapper method that triggers the corresponding nodes when called.


            Returns:
              Any: The result of the original method.

            Side Effects:
              Triggers the corresponding nodes.
            """
            res = method(nodeclassmixininst, *args, **kwargs)

            for (
                node
            ) in nodeclass._instances.values():  # pylint: disable=protected-access
                node.request_trigger()
            return res

        setattr(nodeclassmixininst, method_name, _trigger_on_call_wrapper)


def get_all_nodefunctions(
    cls: Type[NodeClassMixin],
) -> List[Tuple[Callable, str]]:
    """
    Gets all node functions for the given class.

    Args:
      cls (Type[NodeClassMixin]): The class to get the node functions for.

    Returns:
      List[Tuple[Callable, str]]: A list of tuples containing the node functions and their names.
    """
    nodefuncs = []
    for parent in cls.__mro__:
        for name, method in parent.__dict__.items():
            if hasattr(method, "_is_instance_nodefunction"):
                nodefuncs.append((method, name))
    return nodefuncs


class NodeClassMixin(ABC):
    """
    The NodeClassMixin can be used on any class to
    transform transform its methods into node classes.
    Each instance of the class will have its own Nodeclassess,
    making them independend from each other.
    This is especially useful for creating nodes that are
    bound to each other in a specific way, which can be mediated
    by the respective class.

    Attributes:
      NODECLASSID (str): The unique id of the class, forwardet to the node.
      IS_ABSTRACT (bool): Whether the node class is abstract or not.

    Examples:
      >>> class MyNodeClass(NodeClassMixin):
      >>>   NODECLASSID = "my_node_class"
      >>>
      >>>   @instance_nodefunction
      >>>   def add(self, a, b):
      >>>     return a + b
      >>>
      >>>   @add.triggers
      >>>   def eval(self, a, b):
      >>>     # calling this function will trigger the add nodes for this instance
    """

    NODECLASSID: str = None  # type: ignore
    IS_ABSTRACT = True

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Called when a new subclass of NodeClassMixin is created.
        Ensures that NODECLASSID is defined unless the class is abstract.
        """

        super().__init_subclass__(**kwargs)

        # Ensure IS_ABSTRACT defaults to False if not explicitly set in the subclass
        if "IS_ABSTRACT" not in cls.__dict__:
            cls.IS_ABSTRACT = False

        # Check for abstract classes
        if inspect.isabstract(cls) or getattr(cls, "IS_ABSTRACT", False):
            return

        # Ensure NODECLASSID is defined if not abstract
        if cls.NODECLASSID is None:
            raise ValueError(f"NODECLASSID not set for {cls.__name__}")

    def __init__(self, *args, **kwargs):
        """
        Initializes a new instance of the NodeClassMixin class.
        """
        if getattr(self, "IS_ABSTRACT", False):
            raise ValueError("Cannot instantiate abstract NodeClassMixin")
        super().__init__(*args, **kwargs)
        self._node_classes: Dict[str, Type[NodeClassNode]] = (
            {}
        )  # maps method names to node classes
        self._uuid = None
        self._nodes_created = False

        for method, name in get_all_nodefunctions(self.__class__):
            if hasattr(method, "_is_instance_nodefunction"):
                _make_get_node_method(self, method, name)

    @property
    def uuid(self):
        """
        Gets the uuid of the NodeClassMixin instance.

        Args:
          self (NodeClassMixin): The NodeClassMixin instance.

        Returns:
          str: The uuid of the instance.

        Raises:
          ValueError: If the uuid is not set.
        """
        if self._uuid is None:
            raise ValueError("uuid not set, please set using <instance>.uuid = uuid")
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        """
        Sets the uuid of the NodeClassMixin instance.
        """
        if self._uuid is not None:
            raise ValueError("uuid already set")
        self._uuid = value

    def create_nodes(self) -> None:
        """
        Creates all node classes for the NodeClassMixin instance.

        Args:
          self (NodeClassMixin): The NodeClassMixin instance.

        Returns:
          None

        """
        if self._nodes_created:
            return
        for method, name in get_all_nodefunctions(self.__class__):
            _create_node(self, method, name)

        self._nodes_created = True

    def get_nodes(self, method_name) -> List[Node]:
        """
        Gets all instances of a node class for a given method name.

        Args:
          method_name (str): The name of the method to get node instances for.

        Returns:
          List[Node]: A list of all instances of the node class for the given method name.
        """
        return list(
            self.get_nodeclass(  # pylint: disable=protected-access
                method_name
            )._instances.values()
        )

    def get_nodeclass(self, method_name) -> Type[NodeClassNode]:
        """
        Gets the node class for a given method name.

        Args:
          method_name (str): The name of the method to get the node class for.

        Returns:
          Type[NodeClassNode]: The node class for the given method name.
        """
        self.create_nodes()
        return self._node_classes[method_name]

    def get_all_nodeclasses(self) -> List[Type[NodeClassNode]]:
        """
        Gets all node classes for the node mixin.

        Returns:
          List[Type[NodeClassNode]]: A list of all node classes for the node mixin.
        """
        self.create_nodes()
        return list(self._node_classes.values())

    def get_all_nodes(self) -> List[NodeClassNode]:
        """
        Gets all node instances for the node mixin.

        Returns:
          List[NodeClassNode]: A list of all node instances for the node mixin.
        """
        nodes = []
        for m in self.get_all_nodeclasses():
            nodes.extend(
                list(m._instances.values())  # pylint: disable=protected-access
            )
        return nodes
