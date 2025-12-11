## What is the Workermanager?

The Workermanager is a lightweight aiohttp service that supervises all workers on a host. It:

- Maintains worker metadata on disk (`~/.funcnodes/workers/worker_<uuid>.json/.p/.runstate`).
- Spawns, stops, restarts, deletes, and lists workers.
- Acts as a WebSocket hub so UIs can discover and control workers.
- Optionally provisions per-worker virtualenvs and upgrades packages on activation.

By default it listens on `localhost:9380` at `/` for WebSocket clients (no auth by default—see Security).

## Message protocol (WebSocket)

Simple string commands:

- `ping` → `pong`
- `identify` → JSON `{ "class": "WorkerManager", "py": sys.executable }`
- `worker_status` → lists active/inactive workers
- `stop` → stop the manager

JSON commands (selected):

- `{ "type": "new_worker", "kwargs": {...} }` → create worker (options: name, reference, copyLib, copyNS, in_venv toggle)
- `{ "type": "set_active", "workerid": uuid }` → activate (start) worker
- `{ "type": "stop_worker", "workerid": uuid }`
- `{ "type": "restart_worker", "workerid": uuid }`
- `{ "type": "delete_worker", "workerid": uuid }`

Responses/broadcasts include:

- `worker_status` (active/inactive lists)
- `worker_created` / `worker_deleted`
- `set_worker` (full worker config once reachable)
- `progress` (text + progress float) to drive UI HUDs

## Files & liveness

Each worker has:

- `worker_<uuid>.json` — config (host/port/env paths/nodespace path/flags)
- `worker_<uuid>.p` — PID file written by the worker
- `worker_<uuid>.runstate` — textual status during startup/running

Missing or stale files mark workers as inactive; status is refreshed every ~10 s.

## Virtualenv & dependency management

- New workers default to their own venv unless `--not-in-venv` was set.
- On activation, optional `update_on_startup` flags can reinstall `funcnodes`, `funcnodes-core`, and unpinned dependencies.
- CLI helpers `funcnodes worker modules …` run inside the worker env.

## Auto-start behavior

Clients (e.g., `funcnodes runserver`) call `assert_worker_manager_running`: it pings/identifies the manager and, if unreachable, spawns a fresh instance via `python -m funcnodes startworkermanager` (optionally through `subprocess_monitor`).

## Security

- No built-in authentication; expose only behind an authenticated reverse proxy.
- Keep the WS/HTTP ports private; block direct internet access.
- Size limits: large message/store defaults come from worker settings (`MAX_DATA_SIZE`, message expiry).
- TLS termination is not handled by the Workermanager itself; it serves plain HTTP/WebSocket. Terminate TLS at your proxy/load balancer if you need HTTPS/WSS.

## Operations cheat sheet

- Start manager: `funcnodes startworkermanager --host 0.0.0.0 --port 9380`
- List workers: `funcnodes worker list [--full]`
- New worker: `funcnodes worker new --name demo`
- Start worker: `funcnodes worker --name demo start`
- Delete worker: `funcnodes worker --name demo delete`
