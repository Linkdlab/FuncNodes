from typing import Any, Callable, Type, Generic

import js  # pylint: disable=import-error
from js import Object  # pylint: disable=import-error
from pyodide.ffi import (
    JsProxy,
    JsDoubleProxy,
    to_js as pyodide_to_js,
)  # pylint: disable=import-error

from pyscript import format_mime


from .nodespace import NodeSpace, Library
from .node import Node
from .io import NodeIO, Edge
from .mixins import ProxyableMixin, ProxyBase, GenericProxyableMixin


def pythonize_args(args):
    args = [arg.unwrap() if isinstance(arg, JsDoubleProxy) else arg for arg in args]
    args = [arg.to_py() if isinstance(arg, JsProxy) else arg for arg in args]
    args = [arg._obj if isinstance(arg, PyScriptProxyBase) else arg for arg in args]
    return args


undefined = object()


class PyScriptProxyBase(
    Generic[GenericProxyableMixin], ProxyBase[GenericProxyableMixin]
):
    def __getattr__(self, name):
        try:
            attr = super().__getattr__(name)
        except AttributeError:
            attr = undefined

        if attr is not undefined:
            return attr
        attr = getattr(self._obj, name)
        if callable(attr) and not isinstance(attr, ProxyableMixin):

            def _func(*args, **kwargs):
                args = pythonize_args(args)
                res = attr(*args, **kwargs)
                return to_js(res)

            return _func

        return to_js(attr)

    def __setattr__(self, name, value):
        if name == "_obj":
            super().__setattr__(name, value)
        if isinstance(value, JsProxy):
            value = value.to_py()
        setattr(self._obj, name, value)

    def on(self, event: str, cbs: Callable):
        def _cbs(*args, **kwargs):
            jargs = [to_js(arg) for arg in args]
            jkwargs = {k: to_js(v) for k, v in kwargs.items()}
            return to_js(cbs(*jargs, **jkwargs))

        self._obj.on(event, _cbs)

    def once(self, event: str, cbs: Callable):
        def _cbs(*args, **kwargs):
            jargs = [to_js(arg) for arg in args]
            jkwargs = {k: to_js(v) for k, v in kwargs.items()}
            return to_js(cbs(*jargs, **jkwargs))

        self._obj.once(event, _cbs)

    def on_error(self, cbs: Callable):
        def _cbs(*args, **kwargs):
            jargs = [to_js(arg) for arg in args]
            jkwargs = {k: to_js(v) for k, v in kwargs.items()}
            return to_js(cbs(*jargs, **jkwargs))

        self._obj.on_error(_cbs)

    def __call__(self, *args, **kwargs):
        args = pythonize_args(args)
        kwargs = dict(zip(kwargs.keys(), pythonize_args(kwargs.values())))
        ans = self._obj(*args, **kwargs)
        _js = to_js(ans)
        return _js

    def repr_attribut(self, attr: str):
        return to_js(
            format_mime(
                getattr(self._obj, attr),
            )
        )

    @property
    def proxy_class(self):
        return self.__class__.__name__


class LibProxy(PyScriptProxyBase[Library]):
    @classmethod
    def new(cls):
        return to_js(Library())


Library.set_default_proxyclass(LibProxy)


class NodeSpaceProxy(PyScriptProxyBase[NodeSpace]):
    @classmethod
    def new(cls):
        return to_js(NodeSpace())


NodeSpace.set_default_proxyclass(NodeSpaceProxy)


class NodeProxy(PyScriptProxyBase[Node]):
    pass


Node.set_default_proxyclass(NodeProxy)


class NodeIOProxy(PyScriptProxyBase[NodeIO]):
    pass


NodeIO.set_default_proxyclass(NodeIOProxy)


class EdgeProxy(PyScriptProxyBase[Edge]):
    pass


Edge.set_default_proxyclass(EdgeProxy)


class NodeClass(ProxyableMixin):
    NODECLASSES = {}

    def __init__(self, cls: Type[Node]):
        self.cls = cls
        super().__init__()

    @property
    def name(self):
        return self.cls.__name__

    def __call__(self, *args):
        ins = self.cls(*args)
        return ins

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.cls, name)

    @classmethod
    def get_(cls, cls_: Type[Node]):
        if cls_ in cls.NODECLASSES:
            return cls.NODECLASSES[cls_]
        nodeclass = cls(cls_)
        cls.NODECLASSES[cls_] = nodeclass
        return nodeclass


class NodeClassProxy(PyScriptProxyBase[NodeClass]):
    pass


NodeClass.set_default_proxyclass(NodeClassProxy)


def funcnodes_converters(
    val: Any, a: Callable[[Any], JsProxy], b: Callable[[Any, JsProxy], None]
) -> JsProxy:
    # print("funcnodes_converters", val)
    if isinstance(val, set):
        return [funcnodes_converters(v, a, b) for v in val]
    if isinstance(val, ProxyableMixin):
        return pyodide_to_js(val.proxy)
    if isinstance(val, type(Node)):
        if issubclass(val, Node):
            return pyodide_to_js(NodeClass.get_(val).proxy)

    if isinstance(val, Exception):
        return pyodide_to_js(js.Error(val))

    if type(val).__name__ == "DataFrame":  # usually only for pandas
        if val.__class__.__module__ == "pandas.core.frame":
            return to_js(val.to_dict(orient="split"))
    return val


def to_js(jsdata: Any) -> JsProxy:
    if isinstance(jsdata, set):
        jsdata = list(jsdata)
    return pyodide_to_js(
        jsdata,
        dict_converter=Object.fromEntries,
        default_converter=funcnodes_converters,
    )


def get_proxies():
    return {
        "NodeSpace": NodeSpaceProxy,
        "Lib": LibProxy,
        "Node": NodeProxy,
        "NodeIO": NodeIOProxy,
        "Edge": EdgeProxy,
        "NodeClass": NodeClassProxy,
    }
