## Common Issues & Fixes

### “UI can’t connect to Workermanager”
- Ensure the manager is running on the expected host/port (`localhost:9380` by default). Start it with `funcnodes startworkermanager`.
- If using a remote host or custom port, set `--worker_manager_host/--worker_manager_port` in `funcnodes runserver` or update `~/.funcnodes/config.json`.
- Check firewalls/proxy rules; the WS endpoint must be reachable.

### Worker says it is already running / won’t start
- Only one instance of a worker can run at a time. Stop it via `funcnodes worker --name <n> stop`.
- If it still claims to run, delete stale PID file `worker_<uuid>.p` in `~/.funcnodes/workers/` (after confirming no process is active) and start again.
- For venv issues, recreate with `funcnodes worker --name <n> start --not-in-venv` temporarily or rebuild the worker.

### Missing modules in “Manage Libraries”
- The UI reads from the module registry. Verify internet access to `funcnodes_repositories` or provide a mirrored list.
- Install via CLI inside the worker env: `funcnodes worker --name <n> modules install funcnodes-plotly`.
- After install, restart the worker so shelves reload.

### Large uploads or preview errors
- WebSocket messages above the threshold are offloaded to HTTP. If previews fail, check proxy/body-size limits and the env vars `FUNCNODES_WS_WORKER_MAX_SIZE` / `FUNCNODES_WS_WORKER_MAX_DATA_SIZE`.
- For huge data, prefer staging files in the worker `files/` directory and pass paths instead of blobs.

### “Permission denied” writing config or logs
- By default FuncNodes writes to `~/.funcnodes`. Override with `funcnodes --dir .funcnodes` during development or set `FUNCNODES_CONFIG_DIR`.
- On containers, ensure the volume is writable by the FuncNodes user.

### Tests hang or fail with async errors
- Make sure node tests are marked with `@pytest_funcnodes.nodetest` so the plugin sets up an isolated test context.
- Avoid blocking calls in nodes; use `separate_thread=True` or `separate_process=True` for heavy work.

### Docker / port conflicts
- Default UI port is `8000`, Workermanager `9380`. Use `--port` flags or adjust `config.json` to avoid clashes.
- When reverse proxying (nginx/Traefik), keep WS upgrade headers intact for both UI↔manager and manager↔worker sockets.

### How do I reset to a clean state?
- Stop all workers, then move or delete `~/.funcnodes` (or your custom `--dir`) to reset configs, workers, and logs. This deletes worker data—export first if needed.
