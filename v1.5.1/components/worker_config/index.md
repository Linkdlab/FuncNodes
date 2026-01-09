# Worker Configuration

Each worker keeps its own config file at `~/.funcnodes/workers/worker_<uuid>.json`. Key fields include:

- **uuid** / **name** — worker identity.
- **data_path** — worker data dir (nodespace.json, files/, logs).
- **env_path** — virtualenv location (absent when created with `--not-in-venv`).
- **host/port/ssl** — where the worker’s WS/HTTP server listens.
- **update_on_startup** — flags to auto-upgrade `funcnodes`, `funcnodes-core`, and unpinned dependencies on activation.
- **nodespace_path** — path to the current NodeSpace state file.
- **required_heartbeat** — optional timeout for heartbeat enforcement.
- **workertype** — worker class (defaults to WSWorker; extension point for external workers).
- **subprocess_monitor** — optional host/port if using the subprocess monitor.

Creation and lifecycle:

- Generated when you run `funcnodes worker new ...`; updated when workers start/stop.
- The Workermanager reads this file to decide how to spawn and to report status.
- Edits can be made manually for advanced tuning (e.g., changing host/port) — stop the worker first, edit, then restart.

Related liveness files:

- `worker_<uuid>.p` — PID of the running process.
- `worker_<uuid>.runstate` — human-readable startup/run status used by the UI.
