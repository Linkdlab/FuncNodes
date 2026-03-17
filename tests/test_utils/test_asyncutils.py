import json
from pathlib import Path
import subprocess
import sys
import textwrap


def _load_asyncutils():
    asyncutils_path = (
        Path(__file__).resolve().parents[2] / "src/funcnodes/utils/asyncutils.py"
    )

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "funcnodes_utils_asyncutils_under_test", asyncutils_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load asyncutils module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_subprocess(
    code: str, *, timeout_s: float = 5.0
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [sys.executable, "-c", textwrap.dedent(code)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            "async_to_sync deadlocked when called from the event-loop thread"
        ) from exc


def test_async_to_sync_runs_without_running_loop():
    asyncutils = _load_asyncutils()
    async_to_sync = asyncutils.async_to_sync

    async def f():
        return 123

    assert async_to_sync(f)() == 123


def test_async_to_sync_from_running_loop_thread_returns_value():
    asyncutils_path = (
        Path(__file__).resolve().parents[2] / "src/funcnodes/utils/asyncutils.py"
    )

    proc = _run_subprocess(
        f"""
        import asyncio
        import importlib.util
        from pathlib import Path

        path = Path({asyncutils_path.as_posix()!r})
        spec = importlib.util.spec_from_file_location("asyncutils_under_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        async_to_sync = module.async_to_sync

        async def f():
            await asyncio.sleep(0)
            return 123

        async def main():
            return async_to_sync(f)()

        print(asyncio.run(main()))
        """
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "123"


def test_async_to_sync_from_running_loop_thread_propagates_exceptions():
    asyncutils_path = (
        Path(__file__).resolve().parents[2] / "src/funcnodes/utils/asyncutils.py"
    )

    proc = _run_subprocess(
        f"""
        import asyncio
        import importlib.util
        import json
        from pathlib import Path

        path = Path({asyncutils_path.as_posix()!r})
        spec = importlib.util.spec_from_file_location("asyncutils_under_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        async_to_sync = module.async_to_sync

        async def f():
            await asyncio.sleep(0)
            raise ValueError("boom")

        async def main():
            return async_to_sync(f)()

        try:
            asyncio.run(main())
        except Exception as exc:
            print(json.dumps({{"type": type(exc).__name__, "message": str(exc)}}))
        else:
            print(json.dumps({{"type": None, "message": None}}))
        """
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {"type": "ValueError", "message": "boom"}


def test_async_to_sync_from_running_loop_thread_propagates_contextvars():
    asyncutils_path = (
        Path(__file__).resolve().parents[2] / "src/funcnodes/utils/asyncutils.py"
    )

    proc = _run_subprocess(
        f"""
        import asyncio
        import contextvars
        import importlib.util
        from pathlib import Path

        path = Path({asyncutils_path.as_posix()!r})
        spec = importlib.util.spec_from_file_location("asyncutils_under_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        async_to_sync = module.async_to_sync

        value_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "value_var", default=None
        )

        async def f():
            await asyncio.sleep(0)
            return value_var.get()

        async def main():
            value_var.set("hello")
            return async_to_sync(f)()

        print(asyncio.run(main()))
        """
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "hello"
