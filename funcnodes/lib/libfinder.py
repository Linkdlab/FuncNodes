import importlib
from .lib import Shelf
from .libparser import module_to_shelf


def find_shelf(module: str = None) -> Shelf | None:
    # check if identifier is a python module e.g. "funcnodes.lib"
    if module is not None:
        try:
            mod = importlib.import_module(module)
            return module_to_shelf(mod)
        except ModuleNotFoundError:
            pass

    return None
