import sys
import threading


# patching sys.stdout and sys.stderr to ignore OSError exceptions
# this is necessary because the module migh be spawned in a subprocess with pipes
# and the pipes might be closed by the parent process
# this is a workaround to prevent the module from crashing


class PatchesStd:
    def __init__(self, ostd) -> None:
        self.ostd = ostd
        self._patched_attributes = {}
        self._lock = threading.Lock()

    def __getattr__(self, name):
        with self._lock:
            if name in self._patched_attributes:
                return self._patched_attributes[name]

            if hasattr(self.ostd, name):
                a = getattr(self.ostd, name)
                if callable(a):

                    def wrapper(*args, **kwargs):
                        try:
                            return a(*args, **kwargs)
                        except OSError:
                            pass  # Ignore OSError

                    self._patched_attributes[name] = wrapper
                    return wrapper
                return a

            raise AttributeError(f"Attribute {name} not found in {self.ostd}")


def apply_std_patch():
    # Patch both stdout and stderr
    for attr in ["stdout", "stderr"]:
        original = getattr(sys, attr)
        if not original.isatty():
            # Only patch if the stream is not a tty (terminal), probably a pipe
            if not isinstance(original, PatchesStd):
                setattr(sys, attr, PatchesStd(original))


def apply_patches():
    apply_std_patch()
