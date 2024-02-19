from __future__ import annotations
from typing import (
    Dict,
    Callable,
    Any,
    List,
    TypeVar,
    Generic,
    Unpack,
    Protocol,
    Optional,
    Literal,
)
import asyncio
import weakref

from functools import wraps


class AsyncEventManager:
    """
    Manages asyncio events for a given object, allowing for waiting on, setting,
    and clearing events identified by string names.
    """

    def __init__(self, obj: Any) -> None:
        """
        Initialize the EventManager with a reference to the owning object and an empty event dictionary.

        Args:
            obj (Any): The object that owns this EventManager instance.
        """
        self._async_events: Dict[str, asyncio.Event] = {}
        self._obj = weakref.ref(obj)
        self._lock = (
            asyncio.Lock()
        )  # Lock to ensure thread-safe access to the _async_events dictionary.

    @property
    def obj(self) -> Any:
        return self._obj()

    async def wait(self, event: str) -> None:
        """
        Waits for the event to be set before continuing.

        Args:
            event (str): The name of the event to wait for.
        """
        async with self._lock:  # Ensure thread-safe access to the _async_events dictionary.
            if event not in self._async_events:
                self._async_events[event] = asyncio.Event()
            pass

        await self._async_events[event].wait()

    async def set(self, event: str) -> None:
        """
        Sets the event, waking up all waiters.

        Args:
            event (str): The name of the event to set.
        """
        async with self._lock:  # Ensure thread-safe access to the _async_events dictionary.
            if event not in self._async_events:
                self._async_events[event] = asyncio.Event()

            self._async_events[event].set()

    async def clear(self, event: str) -> None:
        """
        Clears the event.

        Args:
            event (str): The name of the event to clear.
        """
        async with self._lock:  # Ensure thread-safe access to the _async_events dictionary.
            if event in self._async_events:
                self._async_events[event].clear()
            pass

    async def set_and_clear(self, event: str, delta: float = 0) -> None:
        """
        Sets the event, briefly allowing other coroutines to process it, then clears the event.

        Args:
            event (str): The name of the event to signal and then clear.
            delta (float): The amount of time to wait before clearing the event in seconds, defaults to 0.
        """

        await self.set(event)  # Set the event to wake up all waiting coroutines.
        await asyncio.sleep(
            max(0, delta)
        )  # Allow other tasks to run, ensuring that they see the event.
        await self.clear(event)  # Clear the event so it can be waited on again.

    async def remove_event(self, event: str) -> None:
        """
        Removes the specified event from the event manager.

        Args:
            event (str): The name of the event to remove.
        """
        async with self._lock:
            if event in self._async_events:
                del self._async_events[event]
            pass


class MessageInArgs(dict):
    """MessageInArgs class is a dictionary that has src as a reserved required keyword
    but also accepts arbitary other ones."""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # if "src" not in self:
        #    raise ValueError("src is a required keyword")

    @property
    def src(self) -> EventEmitterMixin:
        return self["src"]

    @src.setter
    def src(self, value: EventEmitterMixin):
        if not isinstance(value, EventEmitterMixin):
            raise TypeError("src must be an instance of EventEmitterMixin")
        self["src"] = value


GenericMessageInArgs = TypeVar("GenericMessageInArgs", bound=MessageInArgs)


class EventCallback(Protocol, Generic[GenericMessageInArgs]):
    def __call__(self, **kwargs: Unpack[GenericMessageInArgs]) -> Any:  # type: ignore
        """Callback for events.""" ""


class EventErrorCallback(Protocol):
    def __call__(self, error: Exception, src: Any):
        """Callback for error events."""


class EventEmitterMixin:
    """EventEmitterMixin is a mixin class that provides methods for
    emitting and listening to events.
    """

    default_listeners: Dict[str, List[EventCallback]] = {}
    default_error_listeners: List[EventErrorCallback] = []

    def __init__(self, *args, **kwargs):
        self._events: Dict[str, List[EventCallback]] = {}
        self._error_events: List[EventErrorCallback] = []
        super().__init__(*args, **kwargs)
        for event_name, listeners in self.default_listeners.items():
            for listener in listeners:
                self.on(event_name, listener)

        for listener in self.default_error_listeners:
            self.on_error(listener)

    def cleanup(self):
        """Remove all event listeners and perform necessary cleanup before deletion."""
        # Remove specific event listeners
        for event_name in list(self._events.keys()):
            self.off(event_name)

        # Remove error event listeners
        self.off_error()

        # Additional cleanup tasks here

    # Ensure to call cleanup before the object is deleted
    def __del__(self):
        self.cleanup()

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

    def off(self, event_name: str, callback: Optional[EventCallback] = None):
        """removes the specified listener from the listener array for the specified event.
        If no callback is passed, all listeners for the event are removed.
        If the event is empty after removing the listener, it will be removed as well.

        Args:
            event_name (str): The name of the event.
            callback (Optional[EventCallback], optional): The callback function or None (will remove all listeners
            for the event). Defaults to None.
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

    def off_error(self, callback: Optional[EventErrorCallback] = None):
        """removes the specified listener from the listener array for the error event.
        If no callback is passed, all listeners for the error event are removed.

        Args:
            callback (Optional[EventErrorCallback], optional): The callback function or None (will remove all listeners
            for the error event). Defaults to None.
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
            msg = MessageInArgs(src=self)
        if "src" in msg and msg["src"] is not self:
            raise ValueError("src is a reserved keyword")
        msg["src"] = self
        listened = False
        if event_name in self._events:
            for callback in self._events[event_name]:
                callback(**msg)
                listened = True
        if "*" in self._events:
            for callback in self._events["*"]:
                callback(event=event_name, **msg)
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

        if len(self._error_events) > 0:
            for callback in self._error_events:
                callback(error=e, src=self)
            return True
        raise e


EventEmitterMixinGen = TypeVar("EventEmitterMixinGen", bound=EventEmitterMixin)


def emit_before(
    include_kwargs: Literal["all", "none"] | List[str] = "none"
) -> Callable:
    """
    A decorator factory that returns a decorator, which when applied to a function,
    emits an event before the function has been called.

    Parameters
    ----------
    include_kwargs : Union[Literal["all", "none"], List[str]]
        Controls which keyword arguments are included in the message that's emitted.
        - "all": Include all keyword arguments.
        - "none": Include none of the keyword arguments.
        - List[str]: Include only the specified list of keyword argument names.

    Returns
    -------
    Callable
        A decorator that can be applied to a method of a class that inherits from EventEmitterMixin.
    """

    def decorator(func: Callable) -> Callable:
        """
        The actual decorator that wraps the function to emit an event before its execution.

        Parameters
        ----------
        func : Callable
            The function to decorate.

        Returns
        -------
        Callable
            A wrapped function that emits an event before execution.
        """

        # Internal helper function to generate the message for the event
        def gen_msg(self: EventEmitterMixin, **kwargs) -> MessageInArgs:
            """
            Generate a message dictionary to be emitted with the event.

            Parameters
            ----------
            self : EventEmitterMixin
                The instance of the class with EventEmitterMixin.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            MessageInArgs
                The message dictionary to be emitted.
            """
            msg = MessageInArgs(
                src=self
            )  # Initialize the message with the required 'src' key.
            # Update the message with the appropriate keyword arguments based on the include_kwargs parameter.
            if include_kwargs == "all":
                msg.update(kwargs)
            elif isinstance(include_kwargs, list):
                # Include only the specified list of keyword argument names.
                msg.update({k: v for k, v in kwargs.items() if k in include_kwargs})

            return msg

        # Async wrapper for async functions
        @wraps(func)
        async def async_wrapper(self: EventEmitterMixin, *args, **kwargs) -> Any:
            """
            The async wrapper function that first emits an event and then awaits the decorated
            async function, passing through the arguments and keyword arguments.

            Parameters
            ----------
            self : EventEmitterMixin
                The instance of the class with EventEmitterMixin.
            *args
                Arbitrary positional arguments.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            Any
                The result of the original function call.
            """
            msg = gen_msg(self, **kwargs)  # Generate the message to emit.
            self.emit(f"before_{func.__name__}", msg)  # Emit the 'before' event.
            return await func(
                self, *args, **kwargs
            )  # Await and return the result of the function.

        # Synchronous wrapper for sync functions
        @wraps(func)
        def sync_wrapper(self: EventEmitterMixin, *args, **kwargs) -> Any:
            """
            The synchronous wrapper function that first emits an event and then calls the
            decorated function, passing through the arguments and keyword arguments.

            Parameters
            ----------
            self : EventEmitterMixin
                The instance of the class with EventEmitterMixin.
            *args
                Arbitrary positional arguments.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            Any
                The result of the original function call.
            """
            msg = gen_msg(self, **kwargs)  # Generate the message to emit.
            self.emit(f"before_{func.__name__}", msg)  # Emit the 'before' event.
            return func(
                self, *args, **kwargs
            )  # Call and return the result of the function.

        # Choose the correct wrapper based on the function's coroutine status.
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def emit_after(
    include_kwargs: Literal["all", "none"] | List[str] = "none",
    include_result: bool = True,
) -> Callable:
    """
    A decorator factory that returns a decorator, which when applied to a function,
    emits an event after the function has been called.

    Parameters
    ----------
    include_kwargs : Union[Literal["all", "none"], List[str]]
        Controls which keyword arguments are included in the message that's emitted.
        - "all": Include all keyword arguments.
        - "none": Include none of the keyword arguments.
        - List[str]: Include only the specified list of keyword argument names.
    include_result : bool, optional
        Whether to include the result of the function call in the emitted message, by default True.

    Returns
    -------
    Callable
        A decorator that can be applied to a method of a class that inherits from EventEmitterMixin.
    """

    def decorator(func: Callable) -> Callable:
        """
        The actual decorator that wraps the function to emit an event after its execution.

        Parameters
        ----------
        func : Callable
            The function to decorate.

        Returns
        -------
        Callable
            A wrapped function that emits an event after execution.
        """

        # Internal helper function to generate the message for the event
        def gen_msg(self: EventEmitterMixin, result: Any, **kwargs) -> MessageInArgs:
            """
            Generate a message dictionary to be emitted with the event.

            Parameters
            ----------
            self : T
                The instance of the class with EventEmitterMixin.
            result : Any
                The result of the function call.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            MessageInArgs
                The message dictionary to be emitted.
            """
            msg = MessageInArgs(
                src=self
            )  # Initialize the message with the required 'src' key.
            # Update the message with the appropriate keyword arguments based on the include_kwargs parameter.
            if include_kwargs == "all":
                msg.update(kwargs)
            # Include only the specified list of keyword argument names.
            elif isinstance(include_kwargs, list):
                msg.update({k: v for k, v in kwargs.items() if k in include_kwargs})

            # Include the result of the function call if requested.
            if include_result:
                msg["result"] = result

            return msg  # Return the message dictionary.

        @wraps(func)
        async def async_wrapper(self: EventEmitterMixin, *args, **kwargs) -> Any:
            """
            The async wrapper function that awaits the decorated async function, emits an event,
            and then returns the result.

            Parameters
            ----------
            self : T
                The instance of the class with EventEmitterMixin.
            *args
                Arbitrary positional arguments.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            Any
                The result of the original function call.
            """
            r = await func(self, *args, **kwargs)  # Await the function call.
            msg = gen_msg(self, result=r, **kwargs)  # Generate the message to emit.
            self.emit(f"after_{func.__name__}", msg)  # Emit the 'after' event.
            return r  # Return the result of the function call.

        @wraps(func)
        def sync_wrapper(self: EventEmitterMixin, *args, **kwargs) -> Any:
            """
            The synchronous wrapper function that calls the decorated function, emits an event,
            and then returns the result.

            Parameters
            ----------
            self : T
                The instance of the class with EventEmitterMixin.
            *args
                Arbitrary positional arguments.
            **kwargs
                Arbitrary keyword arguments.

            Returns
            -------
            Any
                The result of the original function call.
            """
            r = func(self, *args, **kwargs)  # Call the function.
            msg = gen_msg(self, result=r, **kwargs)  # Generate the message to emit.
            self.emit(f"after_{func.__name__}", msg)  # Emit the 'after' event.
            return r  # Return the result of the function call.

        # Return the correct wrapper based on whether the original function is async or not
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator  # Return the decorator
