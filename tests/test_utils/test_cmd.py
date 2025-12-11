import os
import unittest

# Import all the build functions from your helper script
# For example, if the helper script is named "funcnodes_helper.py":
# from funcnodes_helper import (
#     build_worker_new,
#     build_worker_start,
#     build_worker_list,
#     build_worker_activate,
#     build_worker_listen,
#     build_worker_py,
#     build_startworkermanager,
# )

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


class TestHelperFunctions(unittest.TestCase):
    def test_build_worker_new(self):
        cmd = build_worker_new(
            uuid="123", name="test_worker", workertype="WSWorker", create_only=True
        )
        cmd_str = " ".join(cmd)
        # Check elements in the list
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("new", cmd)
        self.assertIn("--uuid", cmd)
        self.assertIn("123", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("test_worker", cmd)
        self.assertIn("--workertype", cmd)
        self.assertIn("WSWorker", cmd)
        self.assertIn("--create-only", cmd)
        # Check the joined string
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker --uuid 123 --name test_worker new --workertype WSWorker --create-only"
        self.assertEqual(expected, cmd_str)

    def test_build_worker_start(self):
        cmd = build_worker_start(uuid="abc", name="my_worker", workertype="SomeType")
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("start", cmd)
        self.assertIn("--uuid", cmd)
        self.assertIn("abc", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("my_worker", cmd)
        self.assertIn("--workertype", cmd)
        self.assertIn("SomeType", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker --uuid abc --name my_worker start --workertype SomeType"
        self.assertEqual(expected, cmd_str)

    def test_build_worker_list(self):
        # Test full=True
        cmd = build_worker_list(full=True)
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("list", cmd)
        self.assertIn("--full", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker list --full"
        self.assertEqual(expected, cmd_str)

        # Test full=False
        cmd = build_worker_list(full=False)
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("list", cmd)
        self.assertNotIn("--full", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker list"
        self.assertEqual(expected, cmd_str)

    def test_build_worker_activate(self):
        cmd = build_worker_activate(uuid="xyz", name="env_worker")
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("activate", cmd)
        self.assertIn("--uuid", cmd)
        self.assertIn("xyz", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("env_worker", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker --uuid xyz --name env_worker activate"
        self.assertEqual(expected, cmd_str)

    def test_build_worker_listen(self):
        cmd = build_worker_listen(uuid="789", name="log_worker")
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("listen", cmd)
        self.assertIn("--uuid", cmd)
        self.assertIn("789", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("log_worker", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker --uuid 789 --name log_worker listen"
        self.assertEqual(expected, cmd_str)

    def test_build_worker_py(self):
        # Provide multiple args to simulate running a script with arguments
        cmd = build_worker_py(
            uuid="456", name="py_worker", args=["script.py", "--arg", "value"]
        )
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("worker", cmd)
        self.assertIn("py", cmd)
        self.assertIn("--uuid", cmd)
        self.assertIn("456", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("py_worker", cmd)
        self.assertIn("script.py", cmd)
        self.assertIn("--arg", cmd)
        self.assertIn("value", cmd)
        expected = "funcnodes"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " worker --uuid 456 --name py_worker py script.py --arg value"
        self.assertEqual(expected, cmd_str)

    def test_build_startworkermanager(self):
        cmd = build_startworkermanager(port=8080, host="localhost", debug=True)
        cmd_str = " ".join(cmd)
        self.assertIn("funcnodes", cmd)
        self.assertIn("startworkermanager", cmd)
        self.assertIn("--port", cmd)
        self.assertIn("8080", cmd)
        self.assertIn("--host", cmd)
        self.assertIn("localhost", cmd)
        self.assertIn("--debug", cmd)
        expected = "funcnodes --debug"
        if os.environ.get("FUNCNODES_CONFIG_DIR"):
            expected += f" --dir {os.environ.get('FUNCNODES_CONFIG_DIR')}"
        expected += " startworkermanager --port 8080 --host localhost"
        self.assertEqual(expected, cmd_str)


if __name__ == "__main__":
    unittest.main()
