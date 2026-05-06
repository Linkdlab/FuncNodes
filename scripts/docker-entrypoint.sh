#!/bin/sh

# Exit immediately on errors and on unset variable use. This keeps startup
# failures visible instead of letting the container continue half-configured.
set -eu

# Optional runtime dependency refresh.
#
# This is meant for cases where a dependency such as `funcnodes-react-flow` was
# released independently of the main `funcnodes` package. The image still stays
# reproducible by default because the variable is empty unless the user opts in.
if [ -n "${FUNCNODES_UPDATE_PACKAGES:-}" ]; then
    echo "Updating FuncNodes runtime packages: ${FUNCNODES_UPDATE_PACKAGES}"

    # Disable pathname expansion so package names are not accidentally expanded
    # against files in the working directory. Word splitting is intentionally
    # left enabled because the variable is a space-separated package list.
    set -f

    # Install into the non-root user's site-packages. The Dockerfile puts the
    # matching ~/.local/bin path first on PATH so upgraded console scripts win.
    python -m pip install --user --upgrade ${FUNCNODES_UPDATE_PACKAGES}
    set +f
fi

# Default command path.
#
# `docker run image` and `docker run image runserver` both start the FuncNodes
# web UI using the container's environment variables. Extra arguments after
# `runserver` are passed through to the CLI.
if [ "$#" -eq 0 ] || [ "$1" = "runserver" ]; then
    if [ "$#" -gt 0 ]; then
        shift
    fi

    exec funcnodes runserver \
        --host "${FUNCNODES_RUNSERVER_HOST}" \
        --port "${FUNCNODES_RUNSERVER_PORT}" \
        --worker_manager_host "${FUNCNODES_WORKER_MANAGER_HOST}" \
        --worker_manager_port "${FUNCNODES_WORKER_MANAGER_PORT}" \
        "$@"
fi

# Custom command path, for example:
# docker run --rm ghcr.io/linkdlab/funcnodes:latest funcnodes --version
exec "$@"
