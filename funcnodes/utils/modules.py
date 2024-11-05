import csv
import importlib
import subprocess
import sys
import pkg_resources
import requests
from typing import Optional, Dict
from funcnodes_core import AVAILABLE_MODULES, setup, FUNCNODES_LOGGER
from funcnodes_core._setup import setup_module
from funcnodes_core.utils.plugins import InstalledModule
from dataclasses import dataclass


@dataclass
class AvailableRepo:
    package_name: str
    installed: bool
    version: str = ""
    description: str = ""
    entry_point__module: Optional[str] = None
    entry_point__shelf: Optional[str] = None
    moduledata: Optional[InstalledModule] = None
    last_updated: Optional[str] = None
    homepage: Optional[str] = None
    source: Optional[str] = None
    summary: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        data.setdefault("installed", False)
        return cls(**data)


AVAILABLE_REPOS: Dict[str, AvailableRepo] = {}


def load_repo_csv():
    url = "https://raw.githubusercontent.com/Linkdlab/funcnodes_repositories/refs/heads/main/funcnodes_modules.csv"
    resp = requests.get(url, timeout=1)
    if resp.status_code != 200:
        return
    reader = csv.DictReader(resp.text.splitlines(), delimiter=",")
    for line in reader:
        try:
            data = AvailableRepo.from_dict(line)
            if line["package_name"] in AVAILABLE_REPOS:
                moddata = AVAILABLE_REPOS[line["package_name"]].moduledata
                data.moduledata = moddata
            if data.moduledata:
                data.installed = True
            AVAILABLE_REPOS[line["package_name"]] = data

        except Exception as e:
            FUNCNODES_LOGGER.exception(e)


def install_package(package_name, version=None, upgrade=False):
    """
    Install a Python package using pip.

    Parameters:
    - package_name (str): Name of the package to install.
    - version (str, optional): Specific version to install. Defaults to None.
    - upgrade (bool, optional): Whether to upgrade the package if it's already installed. Defaults to False.

    Returns:
    - bool: True if installation was successful or the package is already installed, False otherwise.
    """
    try:
        # Check if the package is already installed
        pkg_resources.get_distribution(package_name)
        if upgrade:
            print(f"Package '{package_name}' is already installed. Upgrading...")
            install_cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                package_name,
            ]
        else:
            print(f"Package '{package_name}' is already installed.")
            return True
    except pkg_resources.DistributionNotFound:
        # Package is not installed; proceed to install
        install_cmd = [sys.executable, "-m", "pip", "install", package_name]

    # If a specific version is requested, modify the install command
    if version:
        install_cmd[-1] = f"{package_name}=={version}"

    try:
        subprocess.check_call(install_cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def install_repo(
    package_name: str, upgrade: bool = False, version=None
) -> Optional[AvailableRepo]:
    if package_name not in AVAILABLE_REPOS:
        return False

    if not install_package(package_name, version, upgrade):
        return None

    # reload imports
    reload_base(with_repos=False)
    if package_name in AVAILABLE_REPOS:
        try_import_repo(package_name)
        return AVAILABLE_REPOS[package_name]

    return None


def try_import_module(name: str) -> Optional[AvailableRepo]:
    repo = (
        AVAILABLE_REPOS.get(name)
        or AVAILABLE_REPOS.get(name.replace("_", "-"))
        or AVAILABLE_REPOS.get(name.replace("-", "_"))
    )
    if not repo:
        try:
            modulename = name.replace("-", "_")
            module = importlib.import_module(modulename)
            module_data = setup_module(InstalledModule(name=name, module=module))

            repo = AvailableRepo(
                package_name=name, installed=True, moduledata=module_data
            )
            AVAILABLE_REPOS[name.replace("_", "-")] = repo
        except Exception as e:
            print(f"Error importing {name}: {e}")

    return try_import_repo(name.replace("_", "-"))


def try_import_repo(name: str) -> Optional[AvailableRepo]:
    if name not in AVAILABLE_REPOS:
        return None

    repo = AVAILABLE_REPOS[name]
    if repo.moduledata:
        return repo
    try:
        modulename = repo.package_name.replace("-", "_")
        module = importlib.import_module(modulename)

        moduledata = setup_module(InstalledModule(name=modulename, module=module))

        repo.moduledata = moduledata
        return repo
    except Exception as e:
        print(f"Error importing {repo.package_name}: {e}")
    return None


def reload_base(with_repos=True):
    setup()
    if with_repos:
        try:
            load_repo_csv()
        except Exception:
            pass
    for repo in AVAILABLE_REPOS.values():
        if repo.moduledata:
            repo.installed = True
        else:
            repo.installed = False

    for modulename, moduledata in AVAILABLE_MODULES.items():
        modulename = modulename.replace("_", "-")  # replace _ with - for pypi
        if modulename in AVAILABLE_REPOS:
            AVAILABLE_REPOS[modulename].installed = True
            AVAILABLE_REPOS[modulename].moduledata = moduledata

        else:
            AVAILABLE_REPOS[modulename] = AvailableRepo(
                package_name=modulename,
                installed=True,
                summary=moduledata.description,
                moduledata=moduledata,
            )
