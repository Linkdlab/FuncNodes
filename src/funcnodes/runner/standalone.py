import asyncio
import hashlib
import json
import socket
import threading
import time
from pathlib import Path
from typing import Optional

import psutil


def pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, 0))
        return int(s.getsockname()[1])


def compute_worker_uuid(fnw_path: Path) -> str:
    digest = hashlib.sha256()
    with open(Path(fnw_path).expanduser().resolve(), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    # Keep the worker UUID compatible with existing funcnodes IDs (32 hex chars).
    return digest.digest()[:16].hex()


def compute_fnw_config_dir(fnw_path: Path) -> Path:
    return fnw_path.parent / f"{fnw_path.stem}_config"


def is_worker_running(
    fnw_path: Path, config_dir: Optional[Path] = None
) -> Optional[int]:
    uuid = compute_worker_uuid(fnw_path)
    workers_dir = (config_dir or compute_fnw_config_dir(fnw_path)) / "workers"
    worker_json = workers_dir / f"worker_{uuid}.json"
    worker_pid = workers_dir / f"worker_{uuid}.p"

    if not worker_json.exists() or not worker_pid.exists():
        return None

    try:
        pid_raw = worker_pid.read_text(encoding="utf-8").strip()
        if not pid_raw:
            return None

        try:
            pid = json.loads(pid_raw)
        except json.JSONDecodeError:
            pid = int(pid_raw)

        if not isinstance(pid, int) or pid <= 0:
            return None

        if not psutil.pid_exists(pid):
            return None
    except Exception:
        return None

    try:
        cfg = json.loads(worker_json.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(cfg, dict):
        return None

    host = cfg.get("host") or "localhost"
    port = cfg.get("port")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        return None

    connect_host = host
    if connect_host in ("0.0.0.0", "::", ""):
        connect_host = "127.0.0.1"

    try:
        with socket.create_connection((connect_host, port), timeout=0.2):
            pass
    except OSError:
        return None

    return port


class StandaloneLauncher:
    def __init__(
        self,
        fnw_path: Path,
        *,
        config_dir: Optional[Path] = None,
        host: str = "localhost",
        ui_port: Optional[int] = None,
        worker_port: Optional[int] = None,
        open_browser: bool = True,
        debug: bool = False,
    ) -> None:
        self.fnw_path = Path(fnw_path).expanduser().resolve()
        self.host = host
        self.ui_port = ui_port
        self.worker_port = worker_port
        self.open_browser = open_browser
        self.debug = debug

        self.config_dir = (
            Path(config_dir).expanduser().resolve()
            if config_dir is not None
            else compute_fnw_config_dir(self.fnw_path)
        )
        self.worker_uuid = compute_worker_uuid(self.fnw_path)

        self.started_worker = False
        self._worker = None
        self._worker_thread: Optional[threading.Thread] = None

    def _ensure_config_dir(self) -> None:
        import funcnodes_core as fn_core

        fn_core.config.reload(str(self.config_dir))
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def ensure_worker(self, *, import_fnw: bool = True) -> int:
        self._ensure_config_dir()

        existing_port = is_worker_running(self.fnw_path, config_dir=self.config_dir)
        if existing_port is not None:
            self.worker_port = existing_port
            self.started_worker = False
            return existing_port

        self._start_worker()

        # Wait until the worker wrote its config + is reachable.
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            port = is_worker_running(self.fnw_path, config_dir=self.config_dir)
            if port is not None:
                self.worker_port = port
                break
            time.sleep(0.05)

        if self.worker_port is None:
            # Fall back to the worker object's current port if reachable-check didn't succeed yet.
            try:
                self.worker_port = int(self._worker.port)  # type: ignore[union-attr]
            except Exception:  # pragma: no cover
                pass

        if import_fnw:
            self._import_fnw()

        if self.worker_port is None:  # pragma: no cover - defensive
            raise RuntimeError("Failed to determine worker port")

        return self.worker_port

    def _start_worker(self) -> None:
        from funcnodes_worker.websocket import WSWorker

        self._worker = WSWorker(
            host=self.host,
            port=self.worker_port,
            uuid=self.worker_uuid,
            debug=self.debug,
        )
        self._worker_thread = self._worker.run_forever_threaded(wait_for_running=True)
        self.started_worker = True

    def _import_fnw(self, *, timeout_s: float = 60.0) -> None:
        if self._worker is None:
            return

        fnw_bytes = self.fnw_path.read_bytes()
        loop = self._worker.loop_manager._loop
        if not loop or not loop.is_running():  # pragma: no cover - defensive
            raise RuntimeError("Worker event loop not running")

        fut = asyncio.run_coroutine_threadsafe(
            self._worker.update_from_export(fnw_bytes),
            loop,
        )
        fut.result(timeout=timeout_s)

    def shutdown(self) -> None:
        if not self.started_worker or self._worker is None:
            return

        loop = self._worker.loop_manager._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._worker.stop)
        else:  # pragma: no cover - defensive
            self._worker.stop()

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5)
