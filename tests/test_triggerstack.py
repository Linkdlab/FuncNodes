import asyncio
import unittest
from funcnodes_core.triggerstack import TriggerStack  # Replace with your actual import


class TestTriggerStack(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for the TriggerStack class.

    The TriggerStack class manages a collection of asyncio.Tasks, providing functionality to
    append, check completion, and await all tasks. These tests cover its functionality, ensuring
    tasks are managed and awaited correctly.
    """

    async def test_append_and_len(self):
        """
        Test that tasks can be appended to the stack and that the length of the stack is accurate.
        """
        stack = TriggerStack()
        task = asyncio.create_task(asyncio.sleep(0.1))
        stack.append(task)
        self.assertEqual(
            len(stack), 1, "Stack length should be 1 after appending a task."
        )

    async def test_check_removes_done_tasks(self):
        """
        Test that the check method removes completed tasks from the stack.
        """
        stack = TriggerStack()
        task = asyncio.create_task(asyncio.sleep(0.1))
        stack.append(task)
        await task  # Wait for the task to complete
        stack.check()
        self.assertEqual(
            len(stack),
            0,
            "Stack should be empty after checking and removing done tasks.",
        )

    async def test_done_returns_false_when_not_done(self):
        """
        Test that the done method returns False when there are incomplete tasks in the stack.
        """
        stack = TriggerStack()
        task = asyncio.create_task(asyncio.sleep(0.1))
        stack.append(task)
        self.assertFalse(
            stack.done(), "Stack should not be done when it has incomplete tasks."
        )

    async def test_done_returns_true_when_empty(self):
        """
        Test that the done method returns True when the stack is empty.
        """
        stack = TriggerStack()
        self.assertTrue(stack.done(), "Stack should be done when it is empty.")

    async def test_awaiting_stack_waits_for_all_tasks(self):
        """
        Test that awaiting the stack waits for all tasks to be completed.
        """
        stack = TriggerStack()
        stack.append(asyncio.create_task(asyncio.sleep(0.1)))
        stack.append(asyncio.create_task(asyncio.sleep(0.2)))
        await stack  # This should wait until all tasks are done
        self.assertTrue(stack.done(), "Stack should be done after awaiting it.")

    async def test_getitem_returns_correct_task(self):
        """
        Test that getting an item from the stack returns the correct task.
        """
        stack = TriggerStack()
        task1 = asyncio.create_task(asyncio.sleep(0.1))
        task2 = asyncio.create_task(asyncio.sleep(0.2))
        stack.append(task1)
        stack.append(task2)
        self.assertEqual(
            stack[0], task1, "First item should be the first task appended."
        )
        self.assertEqual(
            stack[1], task2, "Second item should be the second task appended."
        )

    async def test_tasks_handled_in_reverse_order(self):
        """
        Test that TriggerStack pops tasks in reverse order, as they are handled
        by their completion status, not by their start or finish times.
        """
        stack = TriggerStack()

        async def make_completed_task(name):
            """Create a completed task and add its name to completed_tasks."""
            await asyncio.sleep(0)
            return name

        # Create tasks and add them to the stack in order.
        task1 = asyncio.create_task(make_completed_task("Task1"), name="Task1")
        task2 = asyncio.create_task(make_completed_task("Task2"), name="Task2")
        task3 = asyncio.create_task(make_completed_task("Task3"), name="Task3")
        stack.append(task1)
        stack.append(task2)
        stack.append(task3)
        # Wait for all tasks to complete before checking the order.

        completed_tasks = await stack

        # Verify that tasks were popped off in reverse order.
        self.assertEqual(
            completed_tasks,
            ["Task3", "Task2", "Task1"],
            "Tasks should be handled in reverse order of their addition to the stack.",
        )

        # Create tasks and add them to the stack in order.
        task1 = asyncio.create_task(make_completed_task("Task1"), name="Task1")
        task2 = asyncio.create_task(make_completed_task("Task2"), name="Task2")
        task3 = asyncio.create_task(make_completed_task("Task3"), name="Task3")
        stack.append(task1)
        stack.append(task2)
        stack.append(task3)
        # Wait for all tasks to complete before checking the order.

        completed_tasks = []
        async for task in stack:
            completed_tasks.append(task)
        # Verify that tasks were popped off in reverse order.
        self.assertEqual(
            completed_tasks,
            ["Task3", "Task2", "Task1"],
            "Tasks should be handled in reverse order of their addition to the stack.",
        )


if __name__ == "__main__":
    unittest.main()
