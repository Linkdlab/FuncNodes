import importlib
from typing import Tuple, TypedDict, Union, List, Optional
from .lib import Shelf
from .libparser import module_to_shelf
import os
import sys
import funcnodes as fn
import argparse


class BaseShelfDict(TypedDict):
    """
    TypedDict for a base shelf dictionary.

    Attributes:
      module (str): The name of the module.
    """

    module: str


class PackageShelfDict(BaseShelfDict):
    """
    TypedDict for a package shelf dictionary.

    Attributes:
      package (str): The name of the package.
      version (str): The version of the package.
      module (str): The name of the module.
    """

    package: str
    version: str


class PathShelfDict(BaseShelfDict):
    """
    TypedDict for a path shelf dictionary.

    Attributes:
      path (str): The path to the module.
      module (str): The name of the module.
    """

    path: str
    skip_requirements: bool


ShelfDict = Union[BaseShelfDict, PackageShelfDict, PathShelfDict]


def find_shelf_from_module(
    mod: Union[str, BaseShelfDict],
    args: Optional[List[str]] = None,
) -> Union[Tuple[Shelf, BaseShelfDict], None]:
    """
    Finds a shelf from a module.

    Args:
      mod (Union[str, BaseShelfDict]): The module to find the shelf for.

    Returns:
      Union[Tuple[Shelf, BaseShelfDict], None]: The shelf and the shelf dictionary if found, None otherwise.
    """

    try:
        strmod: str
        if isinstance(mod, dict):
            dat = mod
            strmod = mod["module"]
        else:
            strmod = mod
            dat = BaseShelfDict(module=strmod)

        # submodules = strmod.split(".")

        module = importlib.import_module(strmod)
        # reload module to get the latest version
        try:
            importlib.reload(module)
        except Exception as e:
            pass
        # for submod in submodules[1:]:
        #     mod = getattr(mod, submod)

        return module_to_shelf(module), dat

    except (ModuleNotFoundError, KeyError) as e:
        fn.FUNCNODES_LOGGER.exception(e)
        return None


def find_shelf_from_package(
    pgk: Union[str, PackageShelfDict],
    update: bool = False,
    args: Optional[List[str]] = None,
) -> Union[Tuple[Shelf, PackageShelfDict], None]:
    """
    Finds a shelf from a package.

    Args:
      pgk (Union[str, PackageShelfDict]): The package to find the shelf for.

    Returns:
      Union[Tuple[Shelf, PackageShelfDict], None]: The shelf and the shelf dictionary if found, None otherwise.
    """
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
        data = PackageShelfDict(**data)
        call = f"{sys.executable} -m pip install {data['package']}{data['version']} -q"
        if update:
            call += " --upgrade"
        try:
            os.system(call)
            if (
                update
            ):  # if we updated the package we might need to call it again if the update is new
                os.system(call)
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
    path: Union[str, PathShelfDict],
    args: Optional[List[str]] = None,
) -> Union[Tuple[Shelf, PathShelfDict], None]:
    """
    Finds a shelf from a path.

    Args:
      path (Union[str, PathShelfDict]): The path to find the shelf for.

    Returns:
      Union[Tuple[Shelf, PathShelfDict], None]: The shelf and the shelf dictionary if found, None otherwise.
    """

    if isinstance(path, str):
        parser = argparse.ArgumentParser(description="Parse a path for Funcnodes.")
        parser.add_argument(
            "path",
            type=str,
            help="The path to parse.",
        )
        parser.add_argument(
            "--skip_requirements",
            action="store_true",
            help="Skip installing requirements",
            default=False,
        )
        if args is None:
            args = []

        path = path.replace("\\", os.sep).replace("/", os.sep)
        path = path.strip(os.sep)
        args = [path] + args
        args = parser.parse_args(args=args)

        data = PathShelfDict(
            path=os.path.dirname(os.path.abspath(path)),
            module=os.path.basename(path),
            skip_requirements=args.skip_requirements,
        )
    else:
        data = path

    if not os.path.exists(data["path"]):
        raise FileNotFoundError(f"file {data['path']} not found")

    if data["path"] not in sys.path:
        sys.path.insert(0, data["path"])

    # install requirements
    if not data.get("skip_requirements", False):
        if "pyproject.toml" in os.listdir(data["path"]):
            fn.FUNCNODES_LOGGER.debug(
                f"pyproject.toml found in {data['path']}, generating requirements.txt"
            )
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
            fn.FUNCNODES_LOGGER.debug(
                f"requirements.txt found in {data['path']}, installing requirements"
            )
            # install pip requirements
            os.system(
                f"{sys.executable} -m pip install -r {os.path.join(data['path'],'requirements.txt')}"
            )

    ndata = find_shelf_from_module(data)
    if ndata is not None:
        ndata[1].update(data)
        return ndata


def find_shelf(src: Union[ShelfDict, str]) -> Tuple[Shelf, ShelfDict] | None:
    """
    Finds a shelf from a shelf dictionary or a string.

    Args:
      src (Union[ShelfDict, str]): The shelf dictionary or string to find the shelf for.

    Returns:
      Tuple[Shelf, ShelfDict] | None: The shelf and the shelf dictionary if found, None otherwise.
    """
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

    args = src.split(" ")
    src = args.pop(0)

    if src.startswith("pip://"):
        src = src[6:]
        return find_shelf_from_package(src, update=True, args=args)

    # check if file path:
    if src.startswith("file://"):
        # unifiy path between windows and linux
        src = src[7:]
        return find_shelf_from_path(src, args=args)

    # try to get via pip
    dat = find_shelf_from_module(src, args=args)
    return dat
