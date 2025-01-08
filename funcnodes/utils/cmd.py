from typing import Optional, List


def _build_fn_base(debug=False, **kwargs):
    cmd = ["funcnodes"]
    if debug:
        cmd.append("--debug")
    return cmd


def _build_worker_base_cmd(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs,
) -> List[str]:
    """
    Builds the base worker command with optional UUID and name.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.

    Returns:
        List[str]: The base command-line string as a list.
    """
    cmd = _build_fn_base(**kwargs)
    cmd = ["funcnodes", "worker"]
    if uuid is not None:
        cmd.extend(["--uuid", uuid])
    if name is not None:
        cmd.extend(["--name", name])
    return cmd


def build_worker_new(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = None,
    create_only: bool = False,
    in_venv: Optional[bool] = None,
    **kwargs,
) -> List[str]:
    """
    Build the command for creating a new worker.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.
        workertype (Optional[str]): The type of the worker.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(uuid=uuid, name=name, **kwargs)
    cmd.append("new")
    if workertype is not None:
        cmd.extend(["--workertype", workertype])
    if create_only:
        cmd.append("--create-only")
    if in_venv is not None:
        if not in_venv:
            cmd.append("--not-in-venv")

    return cmd


def build_worker_start(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    workertype: Optional[str] = None,
    **kwargs,
) -> List[str]:
    """
    Build the command for starting an existing worker.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.
        workertype (Optional[str]): The type of the worker.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(uuid=uuid, name=name, **kwargs)
    cmd.append("start")
    if workertype is not None:
        cmd.extend(["--workertype", workertype])
    return cmd


def build_worker_list(full: bool = False, **kwargs) -> List[str]:
    """
    Build the command for listing workers.

    Args:
        full (bool): Whether to show detailed worker information.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(**kwargs)
    cmd.append("list")
    if full:
        cmd.append("--full")
    return cmd


def build_worker_activate(
    uuid: Optional[str] = None, name: Optional[str] = None, **kwargs
) -> List[str]:
    """
    Build the command for activating a worker environment.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(uuid=uuid, name=name, **kwargs)
    cmd.append("activate")
    return cmd


def build_worker_listen(
    uuid: Optional[str] = None, name: Optional[str] = None, **kwargs
) -> List[str]:
    """
    Build the command for listening to a worker's logs.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(uuid=uuid, name=name, **kwargs)
    cmd.append("listen")
    return cmd


def build_worker_py(
    uuid: Optional[str] = None,
    name: Optional[str] = None,
    args: Optional[List[str]] = None,
    **kwargs,
) -> List[str]:
    """
    Build the command for running a Python script in a worker environment.

    Args:
        uuid (Optional[str]): The UUID of the worker.
        name (Optional[str]): The name of the worker.
        *args (str): Additional arguments to pass to the script.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_worker_base_cmd(uuid=uuid, name=name, **kwargs)
    cmd.append("py")
    if args is not None and args:
        cmd.extend(args)
    return cmd


def build_startworkermanager(
    port: Optional[int] = None,
    host: Optional[str] = None,
    **kwargs,
) -> List[str]:
    """
    Build the command for starting a worker manager.

    Args:
        port (Optional[int]): The port to use for the worker manager.
        host (Optional[str]): The host to use for the worker manager.

    Returns:
        List[str]: The command-line string as a list.
    """
    cmd = _build_fn_base(**kwargs)
    cmd.append("startworkermanager")
    if port is not None:
        cmd.extend(["--port", str(port)])
    if host is not None:
        cmd.extend(["--host", host])
    return cmd
