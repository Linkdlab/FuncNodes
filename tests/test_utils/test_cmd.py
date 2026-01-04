import os

# Replace this with the actual name of your helper script file.
from funcnodes.utils.cmd import (
    build_worker_new,
    build_worker_start,
    build_worker_list,
    build_worker_activate,
    build_worker_listen,
    build_worker_py,
    build_startworkermanager,
)

from pytest_funcnodes import funcnodes_test


@funcnodes_test
def test_build_worker_new():
    cmd = build_worker_new(
        uuid="123", name="test_worker", workertype="WSWorker", create_only=True
    )
    cmd_str = " ".join(cmd)
    # Check elements in the list
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "new" in cmd
    assert "--uuid" in cmd
    assert "123" in cmd
    assert "--name" in cmd
    assert "test_worker" in cmd
    assert "--workertype" in cmd
    assert "WSWorker" in cmd
    assert "--create-only" in cmd
    # Check the joined string
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += (
        " worker --uuid 123 --name test_worker new --workertype WSWorker --create-only"
    )
    assert expected == cmd_str


@funcnodes_test
def test_build_worker_start():
    cmd = build_worker_start(uuid="abc", name="my_worker", workertype="SomeType")
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "start" in cmd
    assert "--uuid" in cmd
    assert "abc" in cmd
    assert "--name" in cmd
    assert "my_worker" in cmd
    assert "--workertype" in cmd
    assert "SomeType" in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker --uuid abc --name my_worker start --workertype SomeType"
    assert expected == cmd_str


@funcnodes_test
def test_build_worker_list():
    # Test full=True
    cmd = build_worker_list(full=True)
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "list" in cmd
    assert "--full" in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker list --full"
    assert expected == cmd_str

    # Test full=False
    cmd = build_worker_list(full=False)
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "list" in cmd
    assert "--full" not in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker list"
    assert expected == cmd_str


@funcnodes_test
def test_build_worker_activate():
    cmd = build_worker_activate(uuid="xyz", name="env_worker")
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "activate" in cmd
    assert "--uuid" in cmd
    assert "xyz" in cmd
    assert "--name" in cmd
    assert "env_worker" in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker --uuid xyz --name env_worker activate"
    assert expected == cmd_str


@funcnodes_test
def test_build_worker_listen():
    cmd = build_worker_listen(uuid="789", name="log_worker")
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "listen" in cmd
    assert "--uuid" in cmd
    assert "789" in cmd
    assert "--name" in cmd
    assert "log_worker" in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker --uuid 789 --name log_worker listen"
    assert expected == cmd_str


@funcnodes_test
def test_build_worker_py():
    # Provide multiple args to simulate running a script with arguments
    cmd = build_worker_py(
        uuid="456", name="py_worker", args=["script.py", "--arg", "value"]
    )
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "worker" in cmd
    assert "py" in cmd
    assert "--uuid" in cmd
    assert "456" in cmd
    assert "--name" in cmd
    assert "py_worker" in cmd
    assert "script.py" in cmd
    assert "--arg" in cmd
    assert "value" in cmd
    expected = "funcnodes"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " worker --uuid 456 --name py_worker py script.py --arg value"
    assert expected == cmd_str


@funcnodes_test
def test_build_startworkermanager():
    cmd = build_startworkermanager(port=8080, host="localhost", debug=True)
    cmd_str = " ".join(cmd)
    assert "funcnodes" in cmd
    assert "startworkermanager" in cmd
    assert "--port" in cmd
    assert "8080" in cmd
    assert "--host" in cmd
    assert "localhost" in cmd
    assert "--debug" in cmd
    expected = "funcnodes --debug"
    if os.environ.get("FUNCNODES_CONFIG_DIR"):
        expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
    expected += " startworkermanager --port 8080 --host localhost"
    assert expected == cmd_str
