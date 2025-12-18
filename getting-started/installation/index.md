# Getting started

FuncNodes is a powerful workflow automation system designed for modular and scalable execution. If you're familiar with Python, you can install FuncNodes with [`pip`](#with-pip), the Python package manager. We also aim an stand alone Docker installation and local executables, but they are not yet finished.

## With pip recommended

FuncNodes is published as a Python package and can be installed with `pip`, ideally using a virtual environment. Open a terminal and install FuncNodes with:

```bash
pip install funcnodes
```

```bash
pip install funcnodes=="0.5"
```

This will automatically install all required dependencies, including `funcnodes-core`, `funcnodes-basic`, and other essential packages. FuncNodes always strives to support the latest versions, so there's no need to install dependencies separately.

### Verifying Installation

To confirm that FuncNodes is installed correctly, run:

```bash
funcnodes --version
```

This should display the installed version of FuncNodes. If you encounter any issues, check the [troubleshooting guide](https://linkdlab.github.io/FuncNodes/faq/common-issues/index.md).

______________________________________________________________________
