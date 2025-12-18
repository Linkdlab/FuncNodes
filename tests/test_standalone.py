import json
import os
import socket
import threading
import zipfile
from pathlib import Path
import time

import pytest


def _write_minimal_fnw(
    fnw_path: Path, *, extra_files: dict[str, bytes] | None = None
) -> None:
    extra_files = extra_files or {}
    with zipfile.ZipFile(fnw_path, "w") as zf:
        zf.writestr("config", json.dumps({}).encode("utf-8"))
        zf.writestr("state", json.dumps({}).encode("utf-8"))
        for name, content in extra_files.items():
            zf.writestr(name, content)


@pytest.fixture()
def fnw_path(tmp_path: Path) -> Path:
    fnw_path = tmp_path / "example.fnw"
    _write_minimal_fnw(fnw_path, extra_files={"files/hello.txt": b"hello"})
    return fnw_path


@pytest.fixture()
def _listening_socket():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        yield server
    finally:
        server.close()


def test_pick_free_port_returns_bindable_port():
    from funcnodes.runner.standalone import pick_free_port

    port = pick_free_port(host="127.0.0.1")
    assert isinstance(port, int)
    assert 1024 <= port <= 65535

    # Immediately binding should succeed in normal conditions.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))


def test_compute_worker_uuid_is_deterministic(tmp_path: Path):
    from funcnodes.runner.standalone import compute_worker_uuid

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"test")
    uuid1 = compute_worker_uuid(fnw_path)
    uuid2 = compute_worker_uuid(fnw_path)

    assert uuid1 == uuid2
    assert len(uuid1) == 32
    assert all(c in "0123456789abcdef" for c in uuid1)


def test_compute_worker_uuid_changes_when_file_changes(tmp_path: Path):
    from funcnodes.runner.standalone import compute_worker_uuid

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"one")

    uuid1 = compute_worker_uuid(fnw_path)
    fnw_path.write_bytes(b"two")
    uuid2 = compute_worker_uuid(fnw_path)

    assert uuid1 != uuid2


def test_is_worker_running_returns_none_without_files(fnw_path: Path):
    from funcnodes.runner.standalone import is_worker_running

    assert is_worker_running(fnw_path) == (None, None)


def test_is_worker_running_returns_none_on_invalid_pid(fnw_path: Path):
    from funcnodes.runner.standalone import (
        is_worker_running,
        compute_fnw_config_dir,
        compute_worker_uuid,
    )

    workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    uuid = compute_worker_uuid(fnw_path)
    (workers_dir / f"worker_{uuid}.p").write_text("not-a-pid", encoding="utf-8")
    (workers_dir / f"worker_{uuid}.json").write_text(
        json.dumps({"host": "127.0.0.1", "port": 12345, "ssl": False}),
        encoding="utf-8",
    )

    assert is_worker_running(fnw_path) == (None, None)


def test_is_worker_running_returns_none_on_invalid_json(fnw_path: Path):
    from funcnodes.runner.standalone import (
        is_worker_running,
        compute_fnw_config_dir,
        compute_worker_uuid,
    )

    workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    uuid = compute_worker_uuid(fnw_path)
    (workers_dir / f"worker_{uuid}.p").write_text(str(os.getpid()), encoding="utf-8")
    (workers_dir / f"worker_{uuid}.json").write_text(
        "{ this is not json", encoding="utf-8"
    )

    assert is_worker_running(fnw_path) == (None, None)


def test_is_worker_running_returns_none_when_port_closed(fnw_path: Path):
    from funcnodes.runner.standalone import (
        is_worker_running,
        pick_free_port,
        compute_fnw_config_dir,
        compute_worker_uuid,
    )

    workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    uuid = compute_worker_uuid(fnw_path)
    port = pick_free_port(host="127.0.0.1")
    (workers_dir / f"worker_{uuid}.p").write_text(str(os.getpid()), encoding="utf-8")
    (workers_dir / f"worker_{uuid}.json").write_text(
        json.dumps({"host": "127.0.0.1", "port": port, "ssl": False}),
        encoding="utf-8",
    )

    assert is_worker_running(fnw_path) == (None, None)


def test_is_worker_running_returns_port_when_pid_alive_and_port_open(
    fnw_path: Path, _listening_socket
):
    from funcnodes.runner.standalone import (
        is_worker_running,
        compute_worker_uuid,
        compute_fnw_config_dir,
    )

    workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    uuid = compute_worker_uuid(fnw_path)
    host, port = _listening_socket.getsockname()

    (workers_dir / f"worker_{uuid}.p").write_text(str(os.getpid()), encoding="utf-8")
    (workers_dir / f"worker_{uuid}.json").write_text(
        json.dumps({"host": host, "port": port, "ssl": False}),
        encoding="utf-8",
    )

    assert is_worker_running(fnw_path) == (port, "127.0.0.1")


def test_is_worker_running_uses_config_dir_override(fnw_path: Path, _listening_socket):
    from funcnodes.runner.standalone import is_worker_running, compute_worker_uuid

    custom_config_dir = fnw_path.parent / "custom_config_dir"
    workers_dir = custom_config_dir / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    uuid = compute_worker_uuid(fnw_path)
    host, port = _listening_socket.getsockname()

    (workers_dir / f"worker_{uuid}.p").write_text(str(os.getpid()), encoding="utf-8")
    (workers_dir / f"worker_{uuid}.json").write_text(
        json.dumps({"host": host, "port": port, "ssl": False}),
        encoding="utf-8",
    )

    assert is_worker_running(fnw_path, config_dir=custom_config_dir) == (
        port,
        "127.0.0.1",
    )
    assert is_worker_running(fnw_path) == (None, None)


def test_standalone_launcher_reuses_worker_with_custom_config_dir(fnw_path: Path):
    from funcnodes.runner.standalone import StandaloneLauncher

    custom_config_dir = fnw_path.parent / "custom_config_dir"
    launcher = StandaloneLauncher(
        fnw_path=fnw_path,
        config_dir=custom_config_dir,
        host="127.0.0.1",
        open_browser=False,
        in_venv=False,
    )
    runthread = threading.Thread(target=launcher.run_forever, daemon=True)
    try:
        port = launcher.ensure_worker(import_fnw=True)
        runthread.start()
        assert launcher.started_worker is True

        launcher2 = StandaloneLauncher(
            fnw_path=fnw_path,
            config_dir=custom_config_dir,
            host="127.0.0.1",
            open_browser=False,
        )
        port2 = launcher2.ensure_worker(import_fnw=True)

        assert port2 == port
        assert launcher2.started_worker is False
    finally:
        time.sleep(2)
        try:
            launcher.shutdown()
            if runthread.is_alive():
                runthread.join()
        except Exception:
            pass


def test_standalone_launcher_reuses_running_worker(fnw_path: Path):
    from funcnodes.runner.standalone import (
        StandaloneLauncher,
        compute_fnw_config_dir,
    )

    workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    launcher = None
    runthread = None
    launcher2 = None
    runthread2 = None
    try:
        launcher = StandaloneLauncher(
            fnw_path=fnw_path,
            host="127.0.0.1",
            open_browser=False,
            in_venv=False,
        )

        resolved_port = launcher.ensure_worker(import_fnw=True)
        runthread = threading.Thread(target=launcher.run_forever, daemon=True)
        runthread.start()

        assert launcher.worker_port == resolved_port
        assert launcher.started_worker is True

        launcher2 = StandaloneLauncher(
            fnw_path=fnw_path,
            host="127.0.0.1",
            open_browser=False,
        )

        launcher2.ensure_worker(import_fnw=True)
        runthread2 = threading.Thread(target=launcher2.run_forever, daemon=True)
        runthread2.start()
        assert launcher2.worker_port == resolved_port
        assert launcher2.started_worker is False

    finally:
        time.sleep(2)
        try:
            if launcher:
                launcher.shutdown()
            if runthread:
                if runthread.is_alive():
                    runthread.join()
        except Exception:
            pass

        try:
            if launcher2:
                launcher2.shutdown()
            if runthread2:
                if runthread2.is_alive():
                    runthread2.join()
        except Exception:
            pass


def test_standalone_launcher_starts_worker_and_imports_fnw(fnw_path: Path):
    from funcnodes.runner.standalone import StandaloneLauncher, compute_fnw_config_dir

    launcher = StandaloneLauncher(
        fnw_path=fnw_path,
        host="127.0.0.1",
        open_browser=False,
        in_venv=False,
    )
    runthread = threading.Thread(target=launcher.run_forever, daemon=True)
    try:
        port = launcher.ensure_worker(import_fnw=True)
        runthread.start()
        assert isinstance(port, int)
        assert 1 <= port <= 65535
        assert launcher.started_worker is True

        workers_dir = compute_fnw_config_dir(fnw_path) / "workers"
        assert (workers_dir / f"worker_{launcher.worker_uuid}").exists()
        assert (workers_dir / f"worker_{launcher.worker_uuid}" / "files").exists()
        assert (
            workers_dir / f"worker_{launcher.worker_uuid}" / "files" / "hello.txt"
        ).exists()

        extracted = (
            launcher.config_dir
            / "workers"
            / f"worker_{launcher.worker_uuid}"
            / "files"
            / "hello.txt"
        )
        assert extracted.read_bytes() == b"hello"
    finally:
        try:
            launcher.shutdown()
            if runthread.is_alive():
                runthread.join()
        except Exception:
            pass
