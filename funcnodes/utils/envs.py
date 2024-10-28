import os
import sys
import subprocess
import platform
import json
from typing import List, Dict, TypedDict, Optional
import requests


class PackageListEntry(TypedDict):
    name: str
    version: str


class ProjectURLs(TypedDict, total=False):
    download: Optional[str]
    homepage: Optional[str]
    source: Optional[str]
    tracker: Optional[str]


class Downloads(TypedDict, total=False):
    last_day: int
    last_month: int
    last_week: int


class RequiresDist(TypedDict, total=False):
    requires_dist: List[str]


class ReleaseFile(TypedDict, total=False):
    comment_text: Optional[str]
    digests: Dict[str, str]
    downloads: int
    filename: Optional[str]
    has_sig: bool
    md5_digest: Optional[str]
    packagetype: Optional[str]
    python_version: Optional[str]
    requires_python: Optional[str]
    size: int
    upload_time: Optional[str]
    upload_time_iso_8601: Optional[str]
    url: Optional[str]
    yanked: bool
    yanked_reason: Optional[str]


class Info(TypedDict, total=False):
    author: Optional[str]
    author_email: Optional[str]
    bugtrack_url: Optional[str]
    classifiers: List[str]
    description: Optional[str]
    description_content_type: Optional[str]
    docs_url: Optional[str]
    download_url: Optional[str]
    downloads: Downloads
    dynamic: Optional[str]
    home_page: Optional[str]
    keywords: Optional[str]
    license: Optional[str]
    maintainer: Optional[str]
    maintainer_email: Optional[str]
    name: str
    package_url: Optional[str]
    platform: Optional[str]
    project_url: Optional[str]
    project_urls: ProjectURLs
    provides_extra: Optional[str]
    release_url: Optional[str]
    requires_dist: List[str]
    requires_python: Optional[str]
    summary: Optional[str]
    version: Optional[str]
    yanked: bool
    yanked_reason: Optional[str]


class Release(TypedDict, total=False):
    release_files: List[ReleaseFile]


class Url(TypedDict, total=False):
    comment_text: Optional[str]
    digests: Dict[str, str]
    downloads: int
    filename: Optional[str]
    has_sig: bool
    md5_digest: Optional[str]
    packagetype: Optional[str]
    python_version: Optional[str]
    requires_python: Optional[str]
    size: int
    upload_time: Optional[str]
    upload_time_iso_8601: Optional[str]
    url: Optional[str]
    yanked: bool
    yanked_reason: Optional[str]


class PackageData(TypedDict, total=False):
    info: Info
    last_serial: int
    releases: Dict[str, List[ReleaseFile]]
    urls: List[Url]
    vulnerabilities: List[str]


class EnvManager:
    def __init__(self, env_path):
        self.env_path = env_path
        self.python_exe = self.get_python_executable()

    def get_python_executable(self):
        """Return the path to the Python executable in the virtual environment."""
        if platform.system() == "Windows":
            python_exe = os.path.join(self.env_path, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(self.env_path, "bin", "python")
        if not os.path.isfile(python_exe):
            raise FileNotFoundError(
                f"Python executable not found in virtual environment at {self.env_path}"
            )
        return python_exe

    @classmethod
    def from_current_runtime(cls):
        """Create an EnvManager instance from the current Python runtime."""
        print(sys.executable)
        env_path = os.path.dirname(os.path.dirname(sys.executable))
        return cls(env_path)

    def install_package(self, package_name, version=None, upgrade=False):
        """Install a package in the virtual environment."""
        install_cmd = [self.python_exe, "-m", "pip", "install", package_name]

        # If a specific version is requested, modify the install command
        if version:
            install_cmd[-1] = f'"{package_name}=={version}"'

        if upgrade:
            install_cmd.append("--upgrade")

        try:
            subprocess.check_call(install_cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def all_packages(self) -> List[PackageListEntry]:
        """Return a list of all packages installed in the virtual environment."""
        list_cmd = [self.python_exe, "-m", "pip", "list", "--format=json"]
        try:
            result = subprocess.check_output(list_cmd, universal_newlines=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError("Failed to list packages.") from exc
        try:
            packages = json.loads(result)
            return packages
        except json.JSONDecodeError as exc:
            raise ValueError("Failed to parse pip output.") from exc

    def get_local_package(self, package_name) -> Optional[PackageListEntry]:
        """Return the package entry for the specified package installed in the virtual environment."""
        for pkg in self.all_packages():
            if pkg["name"].lower() == package_name.lower():
                return pkg
        return None

    def get_package_version(self, package_name) -> Optional[str]:
        listentry = self.get_local_package(package_name)
        if listentry:
            return listentry["version"]
        return None

    def get_remote_package(self, package_name) -> Optional[PackageData]:
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            raise ValueError(f"Failed to fetch package data for {package_name}.")

    def package_is_installed(self, package_name):
        """Check if a package is installed in the virtual environment."""
        version = self.get_package_version(package_name)
        return version is not None

    def package_update_available(self, package_name):
        """
        Check if an update is available for the specified package in the given virtual environment.
        If the package is not installed, this method will return False.

        Args:
            package_name (str): Name of the package to check.

        Returns:
            bool: True if an update is available, False otherwise.
            str: The latest version of the package, if available.
            str: The currently installed version of the package, if available.
        """
        local_version = self.get_package_version(package_name)
        if local_version is None:
            return False, None, None

        remote_data = self.get_remote_package(package_name)
        if remote_data is None:
            return False, None, local_version

        if "info" not in remote_data:
            raise ValueError("Invalid package data.")
        if "version" not in remote_data["info"]:
            raise ValueError("Invalid package data.")

        latest_version = remote_data["info"]["version"]
        if latest_version is None:
            raise ValueError("Invalid package data.")

        return latest_version != local_version, latest_version, local_version


def create_virtual_env(env_path):
    """Create a virtual environment at the specified path."""
    import venv

    print(f"Creating virtual environment at {env_path}...")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(env_path)
    print("Virtual environment created.")

    return env_path


def get_or_create_virtual_env(env_path):
    """Return the path to the virtual environment, creating it if necessary."""
    if not os.path.isdir(env_path):
        return create_virtual_env(env_path)
    try:
        return EnvManager(env_path)
    except FileNotFoundError:
        raise ValueError(
            f"Directory {env_path} does not contain a valid virtual environment."
        )


if __name__ == "__main__":
    ev = EnvManager.from_current_runtime()
    # ev.install_package("requests")
    print(ev.package_is_installed("asaf"))
    print(ev.package_update_available("requests"))
    print(ev.package_update_available("funcnodes"))
    print(ev.get_package_version("requests"))
