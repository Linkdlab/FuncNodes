from functools import wraps
import asyncio
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
    - If an event loop is already running, it schedules the coroutine to run in that loop using a separate thread.

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
        - Be cautious when using this in environments where multiple threads or event loops are involved to avoid
          potential deadlocks.
    """

    @wraps(coro_func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # If the event loop is running, run the coroutine in a separate thread
            result: Union[R, None] = None
            exc: Union[Exception, None] = None

            def run_coro():
                nonlocal result, exc
                try:
                    # Schedule the coroutine to run in the existing loop
                    future = asyncio.run_coroutine_threadsafe(
                        coro_func(*args, **kwargs), loop
                    )
                    result = (
                        future.result()
                    )  # This will block until the coroutine is done
                except Exception as e:  # pylint: disable=broad-except
                    exc = e

            thread = threading.Thread(target=run_coro)
            thread.start()
            thread.join()

            if exc is not None:
                raise exc
            return result  # type: ignore
        else:
            # If no event loop is running, create a new one and run the coroutine
            return asyncio.run(coro_func(*args, **kwargs))  # type: ignore

    return wrapper
