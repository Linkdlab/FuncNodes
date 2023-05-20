import os
import re
import shutil
import sys
from io import open

from setuptools import find_packages, setup


CURRENT_PYTHON = sys.version_info[:2]
REQUIRED_PYTHON = (3, 6)

# This check and everything above must remain compatible with Python 2.7.
if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.stderr.write(
        f"""
==========================
Unsupported Python version
==========================

This version of FuncNodes requires Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}, but you're trying
to install it on Python {CURRENT_PYTHON[0]}.{CURRENT_PYTHON[1]}.

"""
    )
    sys.exit(1)


def read(f):
    with open(f, "r", encoding="utf-8") as file:
        return file.read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    s = re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py)
    if s is None:
        raise ValueError("Could not find version string.")
    return s.group(1)


version = get_version("funcnodes")


if sys.argv[-1] == "publish":
    if os.system("pip freeze | grep twine"):
        print("twine not installed.\nUse `pip install twine`.\nExiting.")
        sys.exit()
    os.system("python setup.py sdist bdist_wheel")
    if os.system("twine check dist/*"):
        print("twine check failed. Packages might be outdated.")
        print("Try using `pip install -U twine wheel`.\nExiting.")
        sys.exit()
    os.system("twine upload dist/*")
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    shutil.rmtree("dist")
    shutil.rmtree("build")
    shutil.rmtree("funcnodes.egg-info")
    sys.exit()


install_requires = []

setup(
    name="funcnodes",
    version=version,
    url="https://github.com/Linkdlab/FuncNodes",
    license="MIT",
    license_files="LICENSE.md",
    description="Basic FuncNodes framework",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Julian Kimmig (Linkdlab GmbH)",
    author_email="julian.kimmig@linkdlab.de",
    packages=find_packages(exclude=["tests", "funcnodessampleserver"]),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.6",
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
    ],
    project_urls={
        "Linkdlab": "https://info.linkdlab.de/",
        "Source": "https://github.com/Linkdlab/FuncNodes",
    },
)
