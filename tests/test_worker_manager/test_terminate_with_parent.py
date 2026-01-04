"""
Tests for the terminate_with_parent functionality in run_in_new_process.
"""

import sys

if sys.platform != "emscripten":
    import os
    import time
    import tempfile
    import subprocess
    import pytest
    import psutil

    # Child script that just sleeps and writes its PID to a file
    CHILD_SCRIPT = """
import time
import os
import sys

pid_file = sys.argv[1]
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))

# Sleep for a long time (will be killed by parent death or test cleanup)
time.sleep(300)
"""

    # Parent script that spawns a child with terminate_with_parent option
    PARENT_SCRIPT_TEMPLATE = """
import sys
import time
import os

# Add the src directory to path so we can import funcnodes
sys.path.insert(0, {src_path!r})

from funcnodes.worker.worker_manager import run_in_new_process

child_script = {child_script!r}
pid_file = {pid_file!r}
terminate_with_parent = {terminate_with_parent!r}

# Spawn the child process
p = run_in_new_process(
    sys.executable, child_script, pid_file,
    terminate_with_parent=terminate_with_parent
)

# Write our own PID so the test can find us
parent_pid_file = {parent_pid_file!r}
with open(parent_pid_file, 'w') as f:
    f.write(str(os.getpid()))

# Wait for the child to start and write its PID
for _ in range(50):
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            content = f.read().strip()
            if content:
                break
    time.sleep(0.1)

# Signal that we're ready
ready_file = {ready_file!r}
with open(ready_file, 'w') as f:
    f.write('ready')

# Sleep until we're killed
time.sleep(300)
"""

    def _is_process_running(pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _kill_process_safe(pid: int):
        """Kill a process by PID. Silently ignores if process doesn't exist."""
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            # Process already gone, nothing to do
            return
        except psutil.AccessDenied:
            # Can't access the process
            return

        try:
            proc.terminate()
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process died between check and terminate
            pass

    @pytest.fixture
    def src_path():
        """Return the path to the funcnodes src directory."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "src")
        )

    @pytest.mark.parametrize("terminate_with_parent", [True, False])
    def test_terminate_with_parent(src_path, terminate_with_parent):
        """
        Test that child processes terminate (or not) with parent based on the flag.

        When terminate_with_parent=True:
            - Child should terminate when parent is killed

        When terminate_with_parent=False:
            - Child should continue running after parent is killed
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the child script file
            child_script_path = os.path.join(tmpdir, "child_script.py")
            with open(child_script_path, "w") as f:
                f.write(CHILD_SCRIPT)

            # File paths for communication
            child_pid_file = os.path.join(tmpdir, "child.pid")
            parent_pid_file = os.path.join(tmpdir, "parent.pid")
            ready_file = os.path.join(tmpdir, "ready")

            # Create the parent script
            parent_script = PARENT_SCRIPT_TEMPLATE.format(
                src_path=src_path,
                child_script=child_script_path,
                pid_file=child_pid_file,
                parent_pid_file=parent_pid_file,
                ready_file=ready_file,
                terminate_with_parent=terminate_with_parent,
            )
            parent_script_path = os.path.join(tmpdir, "parent_script.py")
            with open(parent_script_path, "w") as f:
                f.write(parent_script)

            # Start the parent process
            parent_proc = subprocess.Popen(
                [sys.executable, parent_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                # Wait for parent to be ready (child spawned and running)
                timeout = 30
                start = time.time()
                while time.time() - start < timeout:
                    if os.path.exists(ready_file):
                        break
                    time.sleep(0.1)
                else:
                    pytest.fail("Parent process did not become ready in time")

                # Read the child PID
                with open(child_pid_file, "r") as f:
                    child_pid = int(f.read().strip())

                # Verify child is running
                assert _is_process_running(child_pid), "Child process should be running"

                # Read the parent PID
                with open(parent_pid_file, "r") as f:
                    parent_pid = int(f.read().strip())

                # Verify parent is running
                assert _is_process_running(parent_pid), (
                    "Parent process should be running"
                )

                # Kill the parent process
                _kill_process_safe(parent_pid)

                # Wait a bit for the OS to propagate the termination signal
                time.sleep(2)

                # Check if child is still running
                child_running = _is_process_running(child_pid)

                if terminate_with_parent:
                    # Child should have terminated
                    assert not child_running, (
                        "Child process should have terminated when parent died "
                        "(terminate_with_parent=True)"
                    )
                else:
                    # Child should still be running
                    assert child_running, (
                        "Child process should still be running after parent died "
                        "(terminate_with_parent=False)"
                    )
                    # Clean up the child
                    _kill_process_safe(child_pid)

            finally:
                # Cleanup: make sure parent and any child are killed
                try:
                    parent_proc.terminate()
                    parent_proc.wait(timeout=5)
                except Exception:
                    parent_proc.kill()

                # Try to clean up child if it exists
                if os.path.exists(child_pid_file):
                    try:
                        with open(child_pid_file, "r") as f:
                            child_pid = int(f.read().strip())
                        _kill_process_safe(child_pid)
                    except (ValueError, FileNotFoundError):
                        pass

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific Job Object test")
    def test_windows_job_object_creation(src_path):
        """
        Test that the Windows Job Object is created and reused correctly.
        """
        # Import the module to check Windows-specific globals
        sys.path.insert(0, src_path)
        try:
            from funcnodes.worker import worker_manager

            # First call should create the job
            job1 = worker_manager._get_or_create_job()
            assert job1 is not None

            # Second call should return the same job
            job2 = worker_manager._get_or_create_job()
            assert job1 == job2
        finally:
            sys.path.remove(src_path)

    @pytest.mark.skipif(os.name == "nt", reason="POSIX-specific prctl test")
    def test_posix_pdeathsig_set(src_path):
        """
        Test that PR_SET_PDEATHSIG is properly configured on Linux.
        This is a basic smoke test - the actual behavior is tested in
        test_terminate_with_parent.
        """
        # This test verifies the import paths work on POSIX
        sys.path.insert(0, src_path)
        try:
            from funcnodes.worker.worker_manager import run_in_new_process

            # Just verify the function exists and accepts the parameter
            # The actual termination behavior is tested above
            assert callable(run_in_new_process)
        finally:
            sys.path.remove(src_path)
