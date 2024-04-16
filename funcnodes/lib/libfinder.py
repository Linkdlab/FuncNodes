import importlib
from typing import Tuple, TypedDict, Union
from .lib import Shelf
from .libparser import module_to_shelf
import os
import sys
import funcnodes as fn


class BaseShelfDict(TypedDict):
    module: str


class PackageShelfDict(BaseShelfDict):
    package: str
    version: str


class PathShelfDict(BaseShelfDict):
    path: str


ShelfDict = Union[BaseShelfDict, PackageShelfDict, PathShelfDict]


def find_shelf_from_module(
    mod: Union[str, BaseShelfDict]
) -> Union[Tuple[Shelf, BaseShelfDict], None]:
    dat = {}
    try:
        if isinstance(mod, dict):
            dat = mod
            strmod = mod["module"]
        else:
            strmod = mod

        # submodules = strmod.split(".")

        mod = importlib.import_module(strmod)
        # for submod in submodules[1:]:
        #     mod = getattr(mod, submod)
        dat["module"] = strmod
        return module_to_shelf(mod), dat

    except (ModuleNotFoundError, KeyError) as e:
        fn.FUNCNODES_LOGGER.exception(e)
        return None


def find_shelf_from_package(
    pgk: Union[str, PackageShelfDict]
) -> Union[Tuple[Shelf, PackageShelfDict], None]:
    data = {}
    if isinstance(pgk, str):
        ##remove possible version specifier
        stripped_src = pgk.split("=", 1)[0]
        stripped_src = pgk.split(">", 1)[0]
        stripped_src = pgk.split("<", 1)[0]
        stripped_src = pgk.split("~", 1)[0]
        stripped_src = pgk.split("!", 1)[0]
        stripped_src = pgk.split("@", 1)[0]

        data["package"] = stripped_src
        if "/" in pgk:
            data["module"] = pgk.rsplit("/", 1)[-1]
            basesrc = pgk.rsplit("/", 1)[0]
        else:
            data["module"] = data["package"]
            basesrc = pgk
        data["version"] = basesrc.replace(data["package"], "")
        try:
            os.system(
                f"{sys.executable} -m pip install {data['package']}{data['version']} --upgrade -q"
            )
        except Exception as e:
            fn.FUNCNODES_LOGGER.exception(e)
            return None
    else:
        data = pgk

    ndata = find_shelf_from_module(data)
    if ndata is not None:
        ndata[1].update(data)
        return ndata


def find_shelf_from_path(
    path: Union[str, PathShelfDict]
) -> Union[Tuple[Shelf, PathShelfDict], None]:

    if isinstance(path, str):
        path = path.replace("\\", os.sep).replace("/", os.sep)
        path = path.strip(os.sep)

        data = PathShelfDict(
            path=os.path.dirname(os.path.abspath(path)),
            module=os.path.basename(path),
        )
    else:
        data = path

    if not os.path.exists(data["path"]):
        raise FileNotFoundError(f"file {data['path']} not found")

    if data["path"] not in sys.path:
        sys.path.insert(0, data["path"])

    # install requirements

    if "pyproject.toml" in os.listdir(data["path"]):
        fn.FUNCNODES_LOGGER.debug(f"pyproject.toml found, generating requirements.txt")
        # install poetry requirements
        # save current path
        cwd = os.getcwd()
        # cd into the module path
        os.chdir(data["path"])
        # install via poetry
        os.system(f"poetry update --no-interaction")
        os.system(
            f"poetry export --without-hashes -f requirements.txt --output requirements.txt"
        )
        # cd back
        os.chdir(cwd)
    if "requirements.txt" in os.listdir(data["path"]):
        fn.FUNCNODES_LOGGER.debug(f"requirements.txt found, installing requirements")
        # install pip requirements
        os.system(
            f"{sys.executable} -m pip install -r {os.path.join(data['path'],'requirements.txt')}"
        )

    ndata = find_shelf_from_module(data)
    if ndata is not None:
        ndata[1].update(data)
        return ndata


def find_shelf(src: Union[ShelfDict, str]) -> Tuple[Shelf, ShelfDict] | None:
    if isinstance(src, dict):
        if "path" in src:
            dat = find_shelf_from_path(src)
            if dat is not None:
                dat[1].update(src)
            return dat

        if "module" in src:
            dat = find_shelf_from_module(src)

            if dat is not None:
                dat[1].update(src)
                return dat

        if "package" in src:
            dat = find_shelf_from_package(src)
            if dat is not None:
                dat[1].update(src)
                return dat

        return None

    # check if identifier is a python module e.g. "funcnodes.lib"
    fn.FUNCNODES_LOGGER.debug(f"trying to import {src}")
    data = {}

    if src.startswith("pip://"):
        src = src[6:]
        return find_shelf_from_package(src)

    # check if file path:
    if src.startswith("file://"):
        # unifiy path between windows and linux
        src = src[7:]
        return find_shelf_from_path(src)

    # try to get via pip
    os.system(f"{sys.executable} -m pip install {src} -q")
    try:
        mod = importlib.import_module(src)
        return module_to_shelf(mod), {
            "module": src,
        }
    except ModuleNotFoundError as e:
        fn.FUNCNODES_LOGGER.exception(e)

    return None
