import importlib
from .lib import Shelf
from .libparser import module_to_shelf
import os
import sys
import funcnodes as fn


def find_shelf(src: str) -> Shelf | None:
    # check if identifier is a python module e.g. "funcnodes.lib"
    fn.FUNCNODES_LOGGER.debug(f"trying to import {src}")
    # try to use as module
    try:
        mod = importlib.import_module(src)
        return module_to_shelf(mod)
    except ModuleNotFoundError:
        fn.FUNCNODES_LOGGER.debug(f"module {src} not found as python module")

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
        if "pyproject.toml" in os.listdir(mod_path):
            # install poetry requirements
            # save current path
            cwd = os.getcwd()
            # cd into the module path
            os.chdir(mod_path)
            # install via poetry
            os.system(
                f"poetry export --without-hashes -f requirements.txt --output requirements.txt"
            )
            # cd back
            os.chdir(cwd)
        if "requirements.txt" in os.listdir(mod_path):
            # install pip requirements
            os.system(
                f"{sys.executable} -m pip install -r {os.path.join(mod_path,'requirements.txt')}"
            )

        try:
            mod = importlib.import_module(mod_name)
            return module_to_shelf(mod)
        except ModuleNotFoundError as e:
            fn.FUNCNODES_LOGGER.exception(e)
    else:
        # try to get via pip
        os.system(f"{sys.executable} -m pip install {src} -q")
        try:
            mod = importlib.import_module(src)
            return module_to_shelf(mod)
        except ModuleNotFoundError as e:
            fn.FUNCNODES_LOGGER.exception(e)

    return None
