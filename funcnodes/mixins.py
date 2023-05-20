"""
mixins as base classes for funcnodes
"""
from __future__ import annotations
import logging
import sys
from typing import List, Any, Dict, Callable, Generic, TypeVar, Type

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

from ._typing import (
    EventCallback,
    EventErrorCallback,
    MessageInArgs,
)


class EventEmitterMixin:
    """EventEmitterMixin is a mixin class that provides methods for
    emitting and listening to events.
    """

    default_listeners: Dict[str, List[EventCallback]] = {}
    default_error_listeners: List[EventErrorCallback] = []

    @staticmethod
    def catch_and_msg(func: Callable[..., Any]):
        """Decorator for class methods of base EventEmitterMixin,
         that catches any Exception and creates an error event.
        The error event is emitted with the Exception as the first argument.
        """

        def wrapper(self: EventEmitterMixin, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                self.error(exc)

        return wrapper

    @staticmethod
    def catch_msg_and_raise(func: Callable[..., Any]):
        """Decorator for class methods of base EventEmitterMixin,
         that catches any Exception and creates an error event.
        The error event is emitted with the Exception as the first argument.
        Then the exception is raised.
        """

        def wrapper(self: EventEmitterMixin, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                self.error(exc)
                raise exc

        return wrapper

    def __init__(self, *args, **kwargs):
        self._events: Dict[str, List[EventCallback]] = {}
        self._error_events: List[EventErrorCallback] = []
        if not hasattr(self, "logger"):
            self.logger: logging.Logger = None  # type: ignore
        super().__init__(*args, **kwargs)
        self.EventEmitterMixin_log = isinstance(self.logger, logging.Logger)
        for event_name, listeners in self.default_listeners.items():
            for listener in listeners:
                self.on(event_name, listener)

        for listener in self.default_error_listeners:
            self.on_error(listener)

    def on(self, event_name: str, callback: EventCallback):
        """Adds a listener to the end of the listeners array for the specified event.

        Parameters
        ----------
        event_name : str
            The name of the event.
        callback : EventCallback
            The callback function.
        """
        if event_name not in self._events:
            self._events[event_name] = []
        if callback not in self._events[event_name]:
            self._events[event_name].append(callback)

    def on_error(self, callback: EventErrorCallback):
        """Adds a listener to the end of the listeners array for the error event.

        Parameters
        ----------
        callback : EventErrorCallback
            The callback function.
        """
        if callback not in self._error_events:
            self._error_events.append(callback)

    def off(self, event_name: str, callback: EventCallback | None):
        """removes the specified listener from the listener array for the specified event.
        If no callback is passed, all listeners for the event are removed.

        Parameters
        ----------
        event_name : str
            The name of the event.

        callback : EventCallback|None
            The callback function or None (will remove all listeners for the event).
        """
        if event_name not in self._events:
            return
        if callback is None:
            self._events[event_name] = []
        else:
            if callback in self._events[event_name]:
                self._events[event_name].remove(callback)
        if len(self._events[event_name]) == 0:
            del self._events[event_name]

    def off_error(self, callback: EventErrorCallback | None):
        """removes the specified listener from the listener array for the error event.
        If no callback is passed, all listeners for the error event are removed.

        Parameters
        ----------
        callback : EventErrorCallback|None
            The callback function or None (will remove all listeners for the error event).
        """
        if callback is None:
            self._error_events = []
        else:
            if callback not in self._error_events:
                return
            self._error_events.remove(callback)

    def once(self, event_name: str, callback: EventCallback):
        """Adds a one time listener for the event. This listener is invoked
        only the next time the event is fired, after which it is removed.

        Parameters
        ----------
        event_name : str
            The name of the event.
        callback : EventCallback
            The callback function.
        """

        def _callback(*args, **kwargs):
            self.off(event_name, _callback)
            callback(*args, **kwargs)

        self.on(event_name, _callback)

    def once_error(self, callback: EventErrorCallback):
        """Adds a one time listener for the error event. This listener is invoked only the next
        time the error event is fired, after which it is removed.

        Parameters
        ----------
        callback : EventErrorCallback
            The callback function.
        """

        def _callback(error: Exception, src: EventEmitterMixinGen):
            self.off_error(_callback)
            callback(error, src=src)

        self.on_error(_callback)

    def emit(self, event_name: str, msg: MessageInArgs | None = None) -> bool:
        """Execute each of the listeners in order with the supplied arguments.

        Parameters
        ----------
        event_name : str
            The name of the event.
        *args
            The arguments to pass to the listeners.
        **kwargs
            The keyword arguments to pass to the listeners.

        Returns
        -------
        bool
            True if the event had listeners, False otherwise.
        """
        if msg is None:
            msg = MessageInArgs()

        if self.EventEmitterMixin_log:
            self.logger.debug("emitting event %s(%s,%s)", event_name, msg, stacklevel=2)
        if "src" in msg:
            raise ValueError("src is a reserved keyword")
        msg["src"] = self
        listened = False
        if event_name in self._events:
            for callback in self._events[event_name]:
                callback(**msg)
                listened = True
        if "*" in self._events:
            for callback in self._events["*"]:
                callback(event_name, **msg)
                listened = True

        return listened

    def error(self, e: Exception) -> bool:
        """Emits an error event.
        if the error event has listeners, it will call them with the passed error.
        if the error event has no listeners, it will raise the passed error.


        Parameters
        ----------
        e : Exception
            The error to emit.

        Returns
        -------
        bool
            True if the error event had listeners,
            False otherwise (should not happen since, then it should be raised).

        Raises
        ------
        Exception
            Raises the passed Exception of the error event had no listeners.
        """

        self.logger.exception(e)
        if len(self._error_events) > 0:
            for callback in self._error_events:
                callback(error=e, src=self)
            return True
        raise e


EventEmitterMixinGen = TypeVar("EventEmitterMixinGen", bound=EventEmitterMixin)


class ObjectLoggerMixin:
    def __init__(self, *args, **kwargs) -> None:
        logger = logging.getLogger(self.__class__.__name__)

        logger.propagate = False
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s -%(levelname)s:%(name)s(%(lineno)d): %(obj)s: %(message)s"
                )
            )
            logger.addHandler(handler)
        self.logger = logging.LoggerAdapter(logger, {"obj": self})
        print("AAA", self.__class__.__name__, self.logger)
        super().__init__(*args, **kwargs)


GenericProxyableMixin = TypeVar("GenericProxyableMixin", bound="ProxyableMixin")


class ProxyBase(Generic[GenericProxyableMixin]):
    def __init__(self, obj: GenericProxyableMixin):
        self._obj: GenericProxyableMixin = obj
        self._obj.proxy = self  # type: ignore


class ProxyableMixin:
    def __init__(self, *args, **kwargs):
        self._proxy: ProxyBase[Self] | None = None
        super().__init__(*args, **kwargs)

    @property
    def proxy(self) -> ProxyBase[Self]:
        if self._proxy is None:
            self.get_default_proxyclass()(self)
            if self._proxy is None:
                raise AttributeError(
                    f"Proxy not set for {self}, despite having a default proxy class {self.get_default_proxyclass()}"
                )
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: ProxyBase[Self]) -> None:
        if self._proxy is not None:
            raise AttributeError(f"Proxy already set for {self}")
        self._proxy = proxy

    @classmethod
    def set_default_proxyclass(cls, proxyclass: Type[ProxyBase]):
        cls._default_proxyclass = proxyclass

    @classmethod
    def get_default_proxyclass(cls) -> Type[ProxyBase]:
        # check if the class has a default proxy class
        if hasattr(cls, "_default_proxyclass"):
            return cls._default_proxyclass
        # check if the parent class has a default proxy class
        if hasattr(cls, "__bases__"):
            for base in cls.__bases__:
                if issubclass(base, ProxyableMixin):
                    return base.get_default_proxyclass()
        raise AttributeError(f"No default proxy class set for {cls}")
