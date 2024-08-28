import asyncio
import unittest
from unittest.mock import MagicMock
from funcnodes_core.eventmanager import (
    AsyncEventManager,
    EventEmitterMixin,
    MessageInArgs,
    emit_before,
    emit_after,
)


class DummyObject:
    pass


class TestAsyncEventManager(unittest.IsolatedAsyncioTestCase):
    """
    Test case class for the EventManager.
    """

    async def asyncSetUp(self):
        """
        Asynchronous setup for the tests.
        """
        self.obj = DummyObject()  # Mock object to pass into the EventManager
        self.event_manager = AsyncEventManager(self.obj)

    async def test_set_event(self):
        """
        Test that an event can be set.
        """
        event_name = "test_event"
        self.assertFalse(
            self.event_manager._async_events.get(event_name, asyncio.Event()).is_set()
        )

        await self.event_manager.set(event_name)
        self.assertTrue(self.event_manager._async_events[event_name].is_set())

    async def test_wait_event(self):
        """
        Test that waiting on an event works correctly.
        """
        event_name = "test_event"

        # This coroutine will set the event after a short delay
        async def setter():
            await asyncio.sleep(0.1)
            await self.event_manager.set(event_name)

        self.assertEqual(len(self.event_manager._async_events), 0)
        for i in range(2):  # run tqo times to already have the event regisered
            # This will be used to wait for the event to be set
            self.assertEqual(len(self.event_manager._async_events), i)
            # Run both the setter and waiter concurrently
            await asyncio.gather(self.event_manager.wait(event_name), setter())
            self.assertEqual(len(self.event_manager._async_events), 1)

            # Check if waiter_task completed successfully

            self.assertTrue(self.event_manager._async_events[event_name].is_set())

    async def test_clear_event(self):
        """
        Test that clearing an event works correctly.
        """
        event_name = "test_event"
        await self.event_manager.set(event_name)
        self.assertTrue(self.event_manager._async_events[event_name].is_set())

        await self.event_manager.clear(event_name)
        self.assertFalse(self.event_manager._async_events[event_name].is_set())
        await self.event_manager.clear("unknwon")
        self.assertNotIn("unknwon", self.event_manager._async_events)

    async def test_set_and_clear_event(self):
        """
        Test the set_and_clear functionality.
        """
        event_name = "test_event"
        await self.event_manager.set_and_clear(event_name, delta=0.1)

        # Since we have a delay before clearing, the event should be initially set
        self.assertFalse(self.event_manager._async_events[event_name].is_set())

        # Check if another coroutine can wait for the event before it's cleared
        waiter_task = asyncio.create_task(self.event_manager.wait(event_name))
        await asyncio.sleep(0)  # Allow other tasks to run
        await self.event_manager.set(
            event_name
        )  # Set the event so the waiter can continue
        await waiter_task  # Ensure the waiter finishes

        self.assertTrue(waiter_task.done())
        self.assertTrue(self.event_manager._async_events[event_name].is_set())

    async def test_event_manager_stress(self):
        """
        Stress test to set and clear events with many coroutines.
        """
        num_coroutines = 1000  # Number of coroutines to spawn for the test
        event_name = "stress_test_event"
        timeout = 5  # Timeout in seconds for the test

        async def waiter():
            await self.event_manager.wait(event_name)

        async def setter_and_clearer():
            await self.event_manager.set(event_name)
            await asyncio.sleep(0)  # Sleep to allow other tasks to run
            await self.event_manager.clear(event_name)

        # Create tasks for waiting and setting/clearing
        waiters = [asyncio.create_task(waiter()) for _ in range(num_coroutines)]
        setters_and_clearers = [
            asyncio.create_task(setter_and_clearer()) for _ in range(num_coroutines)
        ]

        # Combine all tasks and run them concurrently with a timeout
        all_tasks = waiters + setters_and_clearers
        done, pending = await asyncio.wait(all_tasks, timeout=timeout)

        # If there are any pending tasks, the test is considered a failure
        self.assertFalse(pending, f"Test timed out with {len(pending)} pending tasks.")

        # If any exceptions occurred, re-raise them to fail the test
        for task in done:
            if task.exception():
                raise task.exception()

        # Optionally, assert the event is cleared after stress test
        self.assertFalse(
            self.event_manager._async_events[event_name].is_set(),
            "Event was not cleared after stress test.",
        )

    async def test_high_concurrency(self):
        """
        Test EventManager under high concurrency to ensure it handles many events correctly.
        """
        num_events = 1000  # Number of concurrent events

        # Coroutine to wait for an event
        async def waiter(event_name):
            await self.event_manager.wait(event_name)
            return event_name

        # List of waiter tasks
        waiter_tasks = [
            asyncio.create_task(waiter(f"event_{i}"), name=f"event_{i}")
            for i in range(num_events)
        ]

        # Coroutine to set an event
        async def setter(event_name):
            # await asyncio.sleep(delay)
            await self.event_manager.set(event_name)

        # Set all events after a delay
        for i in range(num_events):
            await setter(f"event_{i}")

        # Wait for all waiter tasks to complete
        done, pending = await asyncio.wait(
            waiter_tasks, return_when=asyncio.ALL_COMPLETED
        )

        # Verify that all tasks completed successfully
        self.assertTrue(
            not pending,
            f"Not all waiter tasks completed: {len(pending)} tasks pending.",
        )
        # Verify that all waiters received their events
        for task in done:
            self.assertEqual(
                task.result(),
                task.get_name(),
                f"Task for {task.get_name()} did not receive its event.",
            )

    async def test_set_and_clear_under_load(self):
        """
        Test the set_and_clear functionality under high load.
        """
        num_events = 1000  # Number of concurrent set_and_clear operations

        # Coroutine to set and clear an event
        async def set_and_clear(event_name):
            await self.event_manager.set_and_clear(event_name, delta=0.001)

        # List of set_and_clear tasks
        set_and_clear_tasks = [
            asyncio.create_task(set_and_clear(f"event_{i}")) for i in range(num_events)
        ]

        # Wait for all set_and_clear tasks to complete
        done, pending = await asyncio.wait(
            set_and_clear_tasks, return_when=asyncio.ALL_COMPLETED
        )

        # Verify that all tasks completed successfully
        self.assertTrue(
            not pending,
            f"Not all set_and_clear tasks completed: {len(pending)} tasks pending.",
        )

    async def test_remove_event(self):
        """
        Test that an event can be removed.
        """
        event_name = "test_event"
        self.assertEqual(len(self.event_manager._async_events), 0)
        await self.event_manager.set_and_clear(event_name)
        self.assertTrue(event_name in self.event_manager._async_events)
        self.assertEqual(len(self.event_manager._async_events), 1)

        await self.event_manager.remove_event(event_name)
        self.assertFalse(event_name in self.event_manager._async_events)
        self.assertEqual(len(self.event_manager._async_events), 0)

        await self.event_manager.remove_event(event_name)
        self.assertFalse(event_name in self.event_manager._async_events)
        self.assertEqual(len(self.event_manager._async_events), 0)


class TestMessageInArgs(unittest.TestCase):
    """Unit tests for the MessageInArgs class."""

    def test_init_with_src_sets_src(self):
        """Should correctly set 'src' if provided on initialization."""
        mock_src = MagicMock(EventEmitterMixin)
        msg_args = MessageInArgs(src=mock_src)
        self.assertEqual(msg_args.src, mock_src)

    def test_set_src_to_invalid_type_raises_type_error(self):
        """Should raise TypeError if 'src' is set to a non-EventEmitterMixin instance."""
        msg_args = MessageInArgs(src=MagicMock(EventEmitterMixin))
        with self.assertRaises(TypeError):
            msg_args.src = "not an EventEmitterMixin"

    def test_set_src_to_valid_type_sets_src(self):
        """Should correctly set 'src' to a new EventEmitterMixin instance."""
        mock_src1 = MagicMock(EventEmitterMixin)
        mock_src2 = MagicMock(EventEmitterMixin)
        msg_args = MessageInArgs(src=mock_src1)
        msg_args.src = mock_src2
        self.assertEqual(msg_args.src, mock_src2)

    def test_init_with_arbitrary_keywords(self):
        """Should accept arbitrary keyword arguments and store them in the dictionary."""
        msg_args = MessageInArgs(src=MagicMock(EventEmitterMixin), foo="bar", number=42)
        self.assertEqual(msg_args["foo"], "bar")
        self.assertEqual(msg_args["number"], 42)


class TestEventEmitterMixin(unittest.TestCase):
    """Unit tests for the EventEmitterMixin class."""

    def setUp(self) -> None:
        """Setup test case environment."""
        self.emitter = EventEmitterMixin()

    def test_on_adds_callback(self):
        """Should add a callback to the specified event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        self.assertIn(callback, self.emitter._events["test_event"])

    def test_double_on_adds_callback_twice(self):
        """Should add a callback to the specified event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        self.emitter.on("test_event", callback)
        self.assertIn(callback, self.emitter._events["test_event"])
        self.assertEqual(len(self.emitter._events["test_event"]), 1)

    def test_on_error_adds_error_callback(self):
        """Should add an error callback."""
        error_callback = MagicMock()
        self.emitter.on_error(error_callback)
        self.assertIn(error_callback, self.emitter._error_events)

    def test_double_on_error_adds_error_callback_twice(self):
        """Should add an error callback."""
        error_callback = MagicMock()
        self.emitter.on_error(error_callback)
        self.emitter.on_error(error_callback)
        self.assertIn(error_callback, self.emitter._error_events)
        self.assertEqual(len(self.emitter._error_events), 1)

    def test_off_removes_callback(self):
        """Should remove a specified callback from an event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        callback2 = MagicMock()
        self.emitter.on("test_event", callback2)
        self.emitter.off("test_event", callback)
        self.assertIn("test_event", self.emitter._events)
        self.assertIn(callback2, self.emitter._events["test_event"])
        self.assertNotIn(callback, self.emitter._events["test_event"])

    def test_off_removes_all_callbacks(self):
        """Should remove all callbacks from an event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        self.emitter.off("test_event")
        self.assertEqual(len(self.emitter._events), 0)

    def test_off_removes_unknown_callback(self):
        """Should remove a specified callback from an event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        callback2 = MagicMock()
        self.emitter.off("test_event", callback2)
        self.assertNotIn(callback2, self.emitter._events["test_event"])
        self.assertIn(callback, self.emitter._events["test_event"])
        self.assertEqual(len(self.emitter._events["test_event"]), 1)

        self.emitter.off("test_event", callback)
        self.assertNotIn("test_event", self.emitter._events)

        self.emitter.off("test_event", callback)

    def test_off_error_removes_error_callback(self):
        """Should remove a specified error callback."""
        error_callback = MagicMock()
        self.emitter.on_error(error_callback)
        self.emitter.off_error(error_callback)
        self.assertNotIn(error_callback, self.emitter._error_events)

    def test_off_error_removes_all_error_callback(self):
        """Should remove a specified error callback."""
        error_callback = MagicMock()
        self.emitter.on_error(error_callback)
        self.emitter.off_error()
        self.assertEqual(len(self.emitter._error_events), 0)

    def test_off_error_removes_unknown_error_callback(self):
        """Should remove a specified error callback."""
        error_callback = MagicMock()
        self.emitter.off_error(error_callback)
        self.assertNotIn(error_callback, self.emitter._error_events)

    def test_once_registers_callback_once(self):
        """Should register a callback to be called only once."""
        callback = MagicMock()
        self.emitter.once("test_event", callback)
        self.emitter.emit("test_event", MessageInArgs(src=self.emitter))
        self.emitter.emit("test_event", MessageInArgs(src=self.emitter))
        callback.assert_called_once()

    def test_once_error_registers_error_callback_once(self):
        """Should register an error callback to be called only once."""
        error_callback = MagicMock()
        self.emitter.once_error(error_callback)
        self.emitter.error(Exception("test"))
        with self.assertRaises(Exception):
            self.emitter.error(Exception("test"))
        error_callback.assert_called_once()

    def test_emit_triggers_callbacks(self):
        """Should call all callbacks associated with the emitted event."""
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        self.emitter.emit("test_event", MessageInArgs(src=self.emitter))
        callback.assert_called()

    def test_emit_with_no_listeners_returns_false(self):
        """Should return False when emitting an event with no listeners."""
        result = self.emitter.emit("test_event", MessageInArgs(src=self.emitter))
        self.assertFalse(result)

    def test_error_raises_if_no_listeners(self):
        """Should raise the exception if no error listeners are registered."""
        with self.assertRaises(Exception) as context:
            self.emitter.error(Exception("test error"))
        self.assertEqual(str(context.exception), "test error")

    def test_error_calls_listeners(self):
        """Should call error listeners with the exception."""
        error_callback = MagicMock()
        self.emitter.on_error(error_callback)
        self.emitter.error(Exception("test error"))
        error_callback.assert_called()

    def test_emit_without_message(self):
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        self.emitter.emit("test_event")
        callback.assert_called_with(src=self.emitter)

    def test_emit_with_false_src(self):
        callback = MagicMock()
        self.emitter.on("test_event", callback)
        with self.assertRaises(ValueError):
            self.emitter.emit("test_event", MessageInArgs(src=EventEmitterMixin()))

    def test_on_all_events(self):
        callback = MagicMock()
        self.emitter.on("*", callback)
        self.emitter.emit("test_event")
        callback.assert_called_with(event="test_event", src=self.emitter)

    def test_default_listener(self):
        class Emiterclass(EventEmitterMixin):
            test_event = MagicMock()
            test_event2 = MagicMock()
            default_listeners = {
                "test_event": [test_event],
            }

            def __init__(self, *args, **kwargs):
                self.default_listeners = {
                    "test_event2": [self.test_event2],
                    **self.default_listeners,
                }
                super().__init__(*args, **kwargs)

        emitter = Emiterclass()

        self.assertIn("test_event", emitter._events)
        self.assertIn("test_event2", emitter._events)
        self.assertEqual(len(emitter._events["test_event"]), 1)
        self.assertEqual(len(emitter._events["test_event2"]), 1)
        self.assertEqual(emitter._events["test_event"][0], Emiterclass.test_event)
        self.assertEqual(emitter._events["test_event2"][0], emitter.test_event2)

        emitter.emit("test_event")
        emitter.test_event.assert_called_with(src=emitter)
        emitter.emit("test_event2")
        emitter.test_event2.assert_called_with(src=emitter)

    def test_default_error_listener(self):
        class Emiterclass(EventEmitterMixin):
            test_event = MagicMock()
            test_event2 = MagicMock()
            default_error_listeners = [test_event]

            def __init__(self, *args, **kwargs):
                (self.default_error_listeners.append(self.test_event2),)
                super().__init__(*args, **kwargs)

        emitter = Emiterclass()
        self.assertIn(emitter.test_event, emitter._error_events)
        self.assertIn(emitter.test_event2, emitter._error_events)
        self.assertEqual(len(emitter._error_events), 2)

        exc = Exception("test error")
        emitter.error(exc)
        emitter.test_event.assert_called_with(src=emitter, error=exc)
        emitter.test_event2.assert_called_with(src=emitter, error=exc)


class TestDecorators(unittest.TestCase):
    """Unit tests for the emit_before and emit_after decorator factories."""

    def setUp(self) -> None:
        """Setup test case environment."""
        self.emitter = MagicMock(EventEmitterMixin)

    def test_emit_before_decorator_emits_event_before_function(self):
        """The emit_before decorator should emit an event before the function call."""
        self.emitter.emit = MagicMock()

        @emit_before()
        def test_function(self):
            return "function_result"

        wrapped_function = test_function(self.emitter)
        self.emitter.emit.assert_called_with(
            "before_test_function", {"src": self.emitter}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_after_decorator_emits_event_after_function(self):
        """The emit_after decorator should emit an event after the function call."""
        self.emitter.emit = MagicMock()

        @emit_after()
        def test_function(self):
            return "function_result"

        wrapped_function = test_function(self.emitter)
        self.emitter.emit.assert_called_with(
            "after_test_function", {"src": self.emitter, "result": "function_result"}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_after_decorator_emits_event_after_function_wo_result(self):
        """The emit_after decorator should emit an event after the function call, but without a result."""
        self.emitter.emit = MagicMock()

        @emit_after(include_result=False)
        def test_function(self):
            return "function_result"

        wrapped_function = test_function(self.emitter)
        self.emitter.emit.assert_called_with(
            "after_test_function", {"src": self.emitter}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_before_decorator_with_specific_kwargs(self):
        """The emit_before decorator should include specified keyword arguments in the event."""
        self.emitter.emit = MagicMock()

        @emit_before(include_kwargs=["foo"])
        def test_function(self, foo, bar):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "before_test_function", {"src": self.emitter, "foo": "foo_value"}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_after_decorator_with_specific_kwargs(self):
        """The emit_after decorator should include specified keyword arguments in the event."""
        self.emitter.emit = MagicMock()

        @emit_after(include_kwargs=["foo"])
        def test_function(self, foo, bar):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "after_test_function",
            {"src": self.emitter, "foo": "foo_value", "result": "function_result"},
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_before_decorator_with_all_kwargs(self):
        """The emit_before decorator should include all keyword arguments in the event if specified."""
        self.emitter.emit = MagicMock()

        @emit_before(include_kwargs="all")
        def test_function(self, **kwargs):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "before_test_function",
            {"src": self.emitter, "foo": "foo_value", "bar": "bar_value"},
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_after_decorator_with_all_kwargs(self):
        """The emit_after decorator should include all keyword arguments in the event if specified."""
        self.emitter.emit = MagicMock()

        @emit_after(include_kwargs="all")
        def test_function(self, **kwargs):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "after_test_function",
            {
                "src": self.emitter,
                "foo": "foo_value",
                "bar": "bar_value",
                "result": "function_result",
            },
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_before_decorator_with_none_kwargs(self):
        """The emit_before decorator should not include keyword arguments in the event if 'none' is specified."""
        self.emitter.emit = MagicMock()

        @emit_before(include_kwargs="none")
        def test_function(self, **kwargs):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "before_test_function", {"src": self.emitter}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_after_decorator_with_none_kwargs(self):
        """The emit_after decorator should not include keyword arguments in the event if 'none' is specified."""
        self.emitter.emit = MagicMock()

        @emit_after(include_kwargs="none")
        def test_function(self, **kwargs):
            return "function_result"

        wrapped_function = test_function(self.emitter, foo="foo_value", bar="bar_value")
        self.emitter.emit.assert_called_with(
            "after_test_function", {"src": self.emitter, "result": "function_result"}
        )
        self.assertEqual(wrapped_function, "function_result")

    def test_emit_before_decorator_async_function(self):
        """The emit_before decorator should correctly handle async functions."""
        self.emitter.emit = MagicMock()

        @emit_before()
        async def async_test_function(self):
            return "async_function_result"

        async_wrapped_function = asyncio.run(async_test_function(self.emitter))
        self.emitter.emit.assert_called_with(
            "before_async_test_function", {"src": self.emitter}
        )
        self.assertEqual(async_wrapped_function, "async_function_result")

    def test_emit_after_decorator_async_function(self):
        """The emit_after decorator should correctly handle async functions."""
        self.emitter.emit = MagicMock()

        @emit_after()
        async def async_test_function(self):
            return "async_function_result"

        async_wrapped_function = asyncio.run(async_test_function(self.emitter))
        self.emitter.emit.assert_called_with(
            "after_async_test_function",
            {"src": self.emitter, "result": "async_function_result"},
        )
        self.assertEqual(async_wrapped_function, "async_function_result")


if __name__ == "__main__":
    unittest.main()

# Run the tests
if __name__ == "__main__":
    unittest.main()
