# Getting started

FuncNodes is a powerful workflow automation system designed for modular and scalable execution. If you're familiar with Python, you can install FuncNodes with [`pip`][pip], the Python package manager. We also aim an stand alone Docker installation and local executables, but they are not yet finished.

<!-- TODO: Docker and standalone -->

[pip]: #with-pip

## With pip <small>recommended</small> { #with-pip data-toc-label="with pip" }

FuncNodes is published as a Python package and can be installed with `pip`, ideally using a virtual environment. Open a terminal and install FuncNodes with:

=== "Latest"

    ```bash
    pip install funcnodes
    ```

=== "Version 0.5"

    ```bash
    pip install funcnodes=="0.5"
    ```

This will automatically install all required dependencies, including `funcnodes-core`, `funcnodes-basic`, and other essential packages. FuncNodes always strives to support the latest versions, so there's no need to install dependencies separately.

### Verifying Installation

To confirm that FuncNodes is installed correctly, run:

```bash
funcnodes --version
```

This should display the installed version of FuncNodes. If you encounter any issues, check the [troubleshooting guide](../faq/common-issues.md).

---
