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

wait_for_worker() {
    worker_host="$1"
    worker_port="$2"
    attempts=60

    # The worker process is started in the background. Poll its websocket port
    # before launching the frontend so the browser receives a reachable worker
    # endpoint immediately.
    while [ "$attempts" -gt 0 ]; do
        if python -c 'import socket, sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=1).close()' "$worker_host" "$worker_port"; then
            return 0
        fi

        attempts=$((attempts - 1))
        sleep 2
    done

    echo "Worker did not become reachable at ${worker_host}:${worker_port}" >&2
    return 1
}

run_single_worker() {
    worker_config="${FUNCNODES_CONFIG_DIR}/workers/worker_${FUNCNODES_SINGLE_WORKER_UUID}.json"
    worker_public_host="${FUNCNODES_SINGLE_WORKER_PUBLIC_HOST:-${FUNCNODES_SINGLE_WORKER_HOST}}"
    worker_connect_host="${FUNCNODES_SINGLE_WORKER_HOST}"

    # Bind hosts such as 0.0.0.0 are valid for the worker process but cannot be
    # used as a client target from inside the container. Use loopback for the
    # local readiness check while keeping the public host for the frontend.
    if [ "$worker_connect_host" = "0.0.0.0" ] || [ "$worker_connect_host" = "::" ] || [ -z "$worker_connect_host" ]; then
        worker_connect_host="127.0.0.1"
    fi

    # Create the fixed worker once. `--not-in-venv` keeps the worker in the
    # container environment, which is already isolated by Docker and can be
    # updated at startup via FUNCNODES_UPDATE_PACKAGES.
    if [ ! -f "$worker_config" ]; then
        funcnodes worker --uuid "${FUNCNODES_SINGLE_WORKER_UUID}" \
            --name "${FUNCNODES_SINGLE_WORKER_NAME}" \
            new --create-only --not-in-venv \
            --host "${FUNCNODES_SINGLE_WORKER_HOST}" \
            --port "${FUNCNODES_SINGLE_WORKER_PORT}"
    fi

    # Start the worker as a background process. The frontend becomes PID 1 after
    # exec below, and Docker will stop the whole container when it exits.
    funcnodes worker --uuid "${FUNCNODES_SINGLE_WORKER_UUID}" start &
    worker_pid="$!"

    if ! wait_for_worker "$worker_connect_host" "${FUNCNODES_SINGLE_WORKER_PORT}"; then
        kill "$worker_pid" 2>/dev/null || true
        wait "$worker_pid" 2>/dev/null || true
        exit 1
    fi

    # Serve the React Flow frontend without Workermanager discovery. The
    # frontend reads /worker from this server and connects directly to the one
    # worker started above.
    exec funcnodes runserver \
        --host "${FUNCNODES_RUNSERVER_HOST}" \
        --port "${FUNCNODES_RUNSERVER_PORT}" \
        --no-browser \
        --no-manager \
        --worker_host "$worker_public_host" \
        --worker_port "${FUNCNODES_SINGLE_WORKER_PORT}" \
        "$@"
}

# Default command path.
#
# `docker run image` and `docker run image runserver` both start the FuncNodes
# web UI using the container's environment variables. Extra arguments after
# `runserver` are passed through to the CLI.
if [ "$#" -eq 0 ] || [ "$1" = "runserver" ]; then
    if [ "$#" -gt 0 ]; then
        shift
    fi

    if [ "${FUNCNODES_DOCKER_MODE:-manager}" = "single-worker" ]; then
        run_single_worker "$@"
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
