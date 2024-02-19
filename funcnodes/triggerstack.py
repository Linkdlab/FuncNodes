import asyncio


class TriggerStack:
    """
    A class that manages a stack of asyncio.Tasks. It provides functionality to append tasks,
    check their completion status, and await the completion of the entire stack of tasks.
    """

    def __init__(self) -> None:
        """
        Initializes a new instance of TriggerStack with an empty stack.
        """
        self._stack = []

    def append(self, node: asyncio.Task) -> None:
        """
        Appends a new asyncio.Task to the stack.

        Args:
            node (asyncio.Task): The asyncio.Task to append to the stack.
        """
        self._stack.append(node)

    def check(self) -> None:
        """
        Checks the stack and removes any completed tasks from the end of the stack.
        """
        # Remove completed tasks from the end of the stack
        while self._stack and self._stack[-1].done():
            self._stack.pop()

    def done(self) -> bool:
        """
        Checks if all tasks in the stack are done.

        Returns:
            bool: True if all tasks are done, False otherwise.
        """
        self.check()  # First, clean up the stack
        return not self._stack  # If the stack is empty, all tasks are done

    def __await__(self):
        """
        Allows an instance of TriggerStack to be awaited. This will await the last task
        in the stack repeatedly until the stack is empty, meaning all tasks are done.

        Yields:
            The result of awaiting the last task in the stack.
        """
        results = []
        while self._stack:
            task = self._stack.pop()
            r = yield from task.__await__()
            results.append(r)
        return results

    def __len__(self) -> int:
        """
        Returns the number of tasks currently in the stack.

        Returns:
            int: The number of tasks in the stack.
        """
        return len(self._stack)

    def __getitem__(self, index: int) -> asyncio.Task:
        """
        Gets the task at the specified index in the stack.

        Args:
            index (int): The index of the task to retrieve.

        Returns:
            asyncio.Task: The task at the specified index.
        """
        return self._stack[index]

    def __aiter__(self):
        """
        Make the TriggerStack an asynchronous iterable.

        Returns:
            An asynchronous iterator over the results of the tasks in the stack.
        """
        return self

    async def __anext__(self):
        """
        Return the next result from the stack or raise StopAsyncIteration
        if there are no more tasks.

        Returns:
            The result of the next task in the stack.

        Raises:
            StopAsyncIteration: If there are no more tasks in the stack.
        """
        if len(self._stack) == 0:
            raise StopAsyncIteration

        task = self._stack.pop()
        return await task
