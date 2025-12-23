import sys

if sys.platform != "emscripten":
    import venvmngr
    import subprocess_monitor
    import subprocess
else:
    venvmngr = None
    subprocess_monitor = None
    subprocess = None
