import importlib
from .lib import Shelf
from .libparser import module_to_shelf
import os
import sys


def find_shelf(src: str) -> Shelf | None:
    # check if identifier is a python module e.g. "funcnodes.lib"

    # try to use as module
    try:
        mod = importlib.import_module(src)
        return module_to_shelf(mod)
    except ModuleNotFoundError:
        pass

    # check if file path:
    if src.startswith("file://"):
        # unifiy path between windows and linux
        src = src.replace("\\", "/")
        src = src[7:].strip("/")
        # check if file exists
        if not os.path.exists(src):
            raise FileNotFoundError(f"file {src} not found")

        # get module path
        mod_path = os.path.dirname(src)
        mod_name = os.path.basename(src)
        if mod_path not in sys.path:
            sys.path.append(mod_path)
        try:
            mod = importlib.import_module(mod_name)
            return module_to_shelf(mod)
        except ModuleNotFoundError:
            pass

    return None
