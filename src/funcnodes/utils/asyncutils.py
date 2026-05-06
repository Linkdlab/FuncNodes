from functools import wraps
import asyncio
import contextvars
import threading
from typing import Any, Awaitable, Callable, TypeVar, Union

# Define type variables for input and output

R = TypeVar("R")


def async_to_sync(coro_func: Callable[..., Awaitable[R]]) -> Callable[..., R]:
    """
    Decorator to run an asynchronous coroutine function in a synchronous context.

    This decorator allows you to call an `async` function as if it were a regular synchronous function.
    It handles the event loop appropriately, whether one is already running or not.

    - If no event loop is running, it creates a new one and runs the coroutine.
    - If an event loop is already running in the current thread, it runs the coroutine in a separate thread with its
      own event loop to avoid blocking the running loop.

    **Parameters:**
        coro_func (Callable[..., Awaitable[Any]]): The asynchronous coroutine function to be converted.

    **Returns:**
        Callable[..., R]: A synchronous function that, when called, executes the coroutine and returns its result.

    **Raises:**
        Exception: Propagates any exception raised during the execution of the coroutine.

    **Usage Example:**

    ```python
    import asyncio

    @async_to_sync
    async def fetch_data(url: str) -> str:
        await asyncio.sleep(1)
        return f"Data from {url}"

    # Synchronously call the asynchronous function
    result = fetch_data("https://example.com")
    print(result)  # Output after 1 second: Data from https://example.com
    ```

    **Notes:**
        - This decorator is useful when you need to integrate asynchronous functions into a synchronous codebase.
        - If called from a running event loop thread, the coroutine is executed in a separate thread with its own
          event loop to avoid deadlocking the current loop.
    """

    @wraps(coro_func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # If no event loop is running, create a new one and run the coroutine.
            return asyncio.run(coro_func(*args, **kwargs))  # type: ignore

        # We're running on the event loop thread.
        #
        # A synchronous wrapper cannot wait for async work scheduled onto the same running loop without blocking
        # that loop (deadlock). Instead, we run the coroutine in a dedicated thread with its own event loop and
        # block this thread until it completes.
        result: Union[R, None] = None
        exc: Union[Exception, None] = None

        ctx = contextvars.copy_context()

        def run_coro():
            nonlocal result, exc
            try:
                result = ctx.run(lambda: asyncio.run(coro_func(*args, **kwargs)))  # type: ignore[arg-type]
            except Exception as e:  # pylint: disable=broad-except
                exc = e

        thread = threading.Thread(target=run_coro)
        thread.start()
        thread.join()

        if exc is not None:
            raise exc
        return result  # type: ignore

    return wrapper
