from collections.abc import Callable
import hashlib
import json
import logging
import socket
import time
from pathlib import Path
from typing import Optional, Tuple

import psutil

logger = logging.getLogger(__name__)


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
) -> Tuple[Optional[int], Optional[str]]:
    uuid = compute_worker_uuid(fnw_path)
    workers_dir = (config_dir or compute_fnw_config_dir(fnw_path)) / "workers"
    worker_json = workers_dir / f"worker_{uuid}.json"
    worker_pid = workers_dir / f"worker_{uuid}.p"

    if not worker_json.exists() or not worker_pid.exists():
        logger.debug(f"No json or pid file found for worker {uuid}")
        return None, None

    try:
        pid_raw = worker_pid.read_text(encoding="utf-8").strip()
        if not pid_raw:
            logger.debug(f"No pid found for worker {uuid}")
            return None, None

        try:
            pid = json.loads(pid_raw)
        except json.JSONDecodeError:
            pid = int(pid_raw)

        if not isinstance(pid, int) or pid <= 0:
            logger.debug(f"Invalid pid {pid} for worker {uuid}")
            return None, None

        if not psutil.pid_exists(pid):
            logger.debug(f"Pid {pid} does not exist for worker {uuid}")
            return None, None
    except Exception:
        logger.debug(f"Exception in is_worker_running for worker {uuid}")
        return None, None

    try:
        cfg = json.loads(worker_json.read_text(encoding="utf-8"))
    except Exception:
        logger.debug(f"Exception in is_worker_running for worker {uuid}")
        return None, None

    if not isinstance(cfg, dict):
        logger.debug(f"Invalid config {cfg} for worker {uuid}")
        return None, None

    host = cfg.get("host") or "localhost"
    port = cfg.get("port")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        logger.debug(f"Invalid port {port} for worker {uuid}")
        return None, None

    connect_host = host
    if connect_host in ("0.0.0.0", "::", ""):
        connect_host = "127.0.0.1"

    try:
        with socket.create_connection((connect_host, port), timeout=0.2):
            pass
    except OSError:
        logger.debug(f"OSError in is_worker_running for worker {uuid}")
        return None, None

    return port, host


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
        on_worker_shutdown: Optional[Callable[[], None]] = None,
        in_venv=True,
    ) -> None:
        self.fnw_path = Path(fnw_path).expanduser().resolve()
        self.host = host
        self.ui_port = ui_port
        self.worker_port = worker_port
        self.open_browser = open_browser
        self.debug = debug
        self.on_worker_shutdown = on_worker_shutdown
        self.running: bool = False
        self.config_dir = (
            Path(config_dir).expanduser().resolve()
            if config_dir is not None
            else compute_fnw_config_dir(self.fnw_path)
        )
        self.worker_uuid = compute_worker_uuid(self.fnw_path)
        self.started_worker = False
        self._ensured = False
        self.in_venv = in_venv

    def _ensure_config_dir(self) -> None:
        import funcnodes_core as fn_core

        fn_core.config.reload(str(self.config_dir))
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def run_forever(self) -> None:
        self.ensure_worker()
        self.running: bool = True
        while self.running:
            time.sleep(2)
            existing_port, existing_host = is_worker_running(
                self.fnw_path, config_dir=self.config_dir
            )
            if existing_port is None:
                self.shutdown()

    def ensure_worker(self, *, import_fnw: bool = True) -> int:
        if self._ensured:
            return self.worker_port
        self._ensured = True
        self._ensure_config_dir()

        existing_port, existing_host = is_worker_running(
            self.fnw_path, config_dir=self.config_dir
        )
        if existing_port is not None:
            self.worker_port = existing_port
            self.host = existing_host
            self.started_worker = False
            return existing_port

        self._start_worker()

        # Wait until the worker wrote its config + is reachable.
        deadline = time.monotonic() + 120.0
        while time.monotonic() < deadline:
            logger.info(f"Waiting for worker to start on port {self.worker_port}")
            port, host = is_worker_running(self.fnw_path, config_dir=self.config_dir)
            if port is not None:
                self.worker_port = port
                self.host = host
                break
            time.sleep(2)
        if port is None:
            raise RuntimeError("Failed to determine worker port")

        self.worker_port = port

        if import_fnw:
            self._import_fnw()

        if self.worker_port is None:  # pragma: no cover - defensive
            raise RuntimeError("Failed to determine worker port")

        return self.worker_port

    def _start_worker(self) -> None:
        from funcnodes.__main__ import _get_worker_conf, start_new_worker
        from funcnodes.worker.worker_manager import start_worker

        try:
            worker_config = _get_worker_conf(
                uuid=self.worker_uuid,
                name=self.fnw_path.stem,
                workertype="WSWorker",
                debug=self.debug,
            )
        except Exception:
            start_new_worker(
                uuid=self.worker_uuid,
                name=self.fnw_path.stem,
                workertype="WSWorker",
                in_venv=self.in_venv,
                create_only=True,
                host=self.host,
                port=self.worker_port,
            )
            worker_config = _get_worker_conf(
                uuid=self.worker_uuid,
                name=self.fnw_path.stem,
                workertype="WSWorker",
                debug=self.debug,
            )

        start_worker(worker_config)
        logger.info(f"Worker started with {worker_config}")
        self.worker_port = worker_config["port"]

        self.started_worker = True

    def _import_fnw(self) -> None:
        from funcnodes.__main__ import worker_command_task
        import base64

        base64_fnw_bytes = base64.b64encode(self.fnw_path.read_bytes()).decode("utf-8")

        worker_command_task(
            command="update_from_export", uuid=self.worker_uuid, data=base64_fnw_bytes
        )

    def shutdown(self) -> None:
        logger.info(
            "Shutting down standalone launcher with running state %s", self.running
        )
        if self.running:
            self.running = False
            if self.on_worker_shutdown:
                self.on_worker_shutdown()
            if self.started_worker:
                port, host = is_worker_running(
                    self.fnw_path, config_dir=self.config_dir
                )
                if port is not None:
                    from funcnodes.__main__ import worker_command_task

                    worker_command_task(command="stop_worker", uuid=self.worker_uuid)
