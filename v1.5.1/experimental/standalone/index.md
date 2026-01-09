# Standalone

`funcnodes standalone` is an **experimental** way to open a single `.fnw` workflow file with a **dedicated worker**, without relying on a global Workermanager.

It is designed for the “double‑click a workflow file and run it” experience, while keeping each workflow isolated.

Experimental

- The file-association integration (`--register`) is OS/desktop dependent.
- The standalone runtime is stable enough for day-to-day use, but still evolving.

______________________________________________________________________

## What it does (high level)

When you run:

```bash
funcnodes standalone path/to/workflow.fnw
```

FuncNodes will:

1. Resolve and validate the `.fnw` path.
1. Choose a **workflow-local config directory** (default: next to the file).
1. Ensure a **dedicated worker** exists (and start it if needed).
1. Import the `.fnw` content into that worker.
1. Start a small UI server (React Flow UI) connected to that worker.
1. Optionally open your browser.

This gives you a self-contained “one workflow = one worker” runtime, without running a shared Workermanager process.

______________________________________________________________________

## Why standalone exists

The normal “server mode” (`funcnodes runserver`) is optimized for a multi-worker setup:

- a Workermanager supervises workers,
- the UI discovers workers via the manager,
- workers often live under a shared base directory like `~/.funcnodes`.

Standalone is optimized for a different use case:

- you have **one `.fnw` file** and want to open/run it quickly,
- you want the worker state and files to live **close to the workflow** (or in a per-project location),
- you want an easy path to “open with FuncNodes” via OS file associations.

______________________________________________________________________

## CLI usage

### Open a workflow

```bash
funcnodes standalone ./example.fnw
```

### Important options

| Option                               | Meaning                                                                                |
| ------------------------------------ | -------------------------------------------------------------------------------------- |
| `--config-dir <path>`                | Override the workflow-local config directory (default: `<fnw_dir>/<fnw_stem>_config`). |
| `--host <host>`                      | Host to bind the UI/worker to (default: `localhost`).                                  |
| `--worker-port <port>`               | Force a specific worker port (default: auto).                                          |
| `--ui-port <port>` / `--port <port>` | Force a specific UI port (default: auto).                                              |
| `--no-browser`                       | Don’t open a browser automatically.                                                    |
| `--debug`                            | Enable debug logging (also affects worker startup behavior).                           |

### Register “open .fnw with FuncNodes” (desktop integration)

```bash
funcnodes standalone --register
```

This creates a small launcher script that calls the exact Python interpreter that executed `funcnodes` at registration time, then configures your OS so `.fnw` files open with it.

______________________________________________________________________

## Workflow-local config directory

Standalone intentionally uses a **workflow-local base directory**.

By default, for a workflow file:

```text
/path/to/MyWorkflow.fnw
```

the config directory is:

```text
/path/to/MyWorkflow_config/
```

This directory behaves like a mini `~/.funcnodes` for that workflow. It stores worker metadata, PID files, logs, and (depending on your worker settings) environments and data.

Project-local isolation

For reproducible projects, consider keeping the `.fnw` and its `_config` directory in your repo, so your workflow state travels with the project.

______________________________________________________________________

## How the worker is identified (UUID)

Standalone computes a worker UUID from the **file contents**:

- it hashes the `.fnw` bytes (SHA‑256),
- then uses a 32-hex-character prefix as the worker UUID.

Implications:

- Opening the same `.fnw` **content** gives the same UUID → stable identity.
- Changing the file content changes the UUID → you may end up with multiple `worker_<uuid>.json` files over time inside the same `<stem>_config/workers/` directory.

______________________________________________________________________

## “Already running” detection and reuse

Before starting a new worker, standalone checks whether the worker is already running by looking in:

- `<config_dir>/workers/worker_<uuid>.json` (worker config)
- `<config_dir>/workers/worker_<uuid>.p` (PID)

and then verifying the port is reachable.

If a worker for that `.fnw` is already running, standalone will **reuse** it instead of spawning another instance.

______________________________________________________________________

## Importing the workflow into the worker

After ensuring the worker is reachable, standalone imports the `.fnw` into the worker:

- reads the `.fnw` bytes,
- base64‑encodes them,
- sends a worker command to update its nodespace from that export.

This is what makes the opened worker reflect the content of the clicked `.fnw` file.

______________________________________________________________________

## UI server behavior

Standalone starts the React Flow UI server and connects it directly to the worker (no manager in between).

- The UI port is chosen automatically unless `--ui-port/--port` is set.
- The browser is opened by default; use `--no-browser` to disable.

______________________________________________________________________

## Shutdown behavior

- Pressing `Ctrl+C` in the terminal triggers a shutdown sequence.
- If standalone started the worker itself, it will also request the worker to stop.
- If the worker stops unexpectedly, standalone will detect that and shut down as well.

______________________________________________________________________

## Desktop integration: `--register`

`funcnodes standalone --register` performs two things:

1. **Write a launcher script** into your FuncNodes config directory:
1. Windows: `.../scripts/fnw_open.cmd`
1. Linux/macOS: `.../scripts/fnw_open.sh`
1. **Register** this launcher as the default opener for `.fnw` files (best-effort, per user).

### Where the launcher is written

The launcher is written to the FuncNodes **base config dir**:

- default: `~/.funcnodes/`
- override via env: `FUNCNODES_CONFIG_DIR=/somewhere`
- override via CLI: `funcnodes --dir /somewhere standalone --register`

This is intentionally separate from the per-workflow `--config-dir` used when actually opening a `.fnw`.

### What the launcher does

The launcher embeds:

- `PY=<sys.executable>` at registration time

and then runs:

```text
PY -m funcnodes standalone "<clicked-file.fnw>"
```

This avoids relying on PATH entrypoints and ensures the same Python environment is used.

______________________________________________________________________

## OS-specific registration details

### Windows

Standalone registration:

- writes registry keys under `HKCU\\Software\\Classes\\` (current user, no admin required),
- registers a ProgID (`FuncNodes.WorkerFile`),
- sets:
- `shell\\open\\command` → `"path\\to\\fnw_open.cmd" "%1"`
- `DefaultIcon` → `"path\\to\\fnw_icon.ico",0`
- copies the icon from the package into your config scripts directory as `fnw_icon.ico`.

Windows default-app behavior

Some Windows setups may still require a user confirmation in “Default apps” depending on existing `UserChoice` settings.

### Linux (XDG desktops)

Standalone registration:

- writes a MIME type definition for `.fnw` (`application/x-funcnodes-fnw`),
- writes a `.desktop` launcher entry that calls your `fnw_open.sh`,
- sets the default handler using `xdg-mime` (if available),
- copies icons:
- app icon: `fnw_icon.png` under the FuncNodes config scripts directory
- MIME icon: `application-x-funcnodes-fnw.png` under `$XDG_DATA_HOME/icons/hicolor/.../mimetypes/`

It will attempt (best effort) to run:

- `update-mime-database`
- `update-desktop-database`
- `gtk-update-icon-cache`

If these tools are missing, you may need to run the equivalent commands manually or log out/in depending on your desktop environment.

### macOS

Standalone registration creates (best-effort) an app bundle:

- `~/.../FuncNodesFNW.app` in the FuncNodes base config dir
- includes `Info.plist` with `.fnw` document types and `CFBundleIconFile`
- copies `fnw_icon.icns` into `Contents/Resources/`

Because Finder delivers opened files via Apple Events (not `$1` argv), the bundle is generated as an AppleScript “droplet” (compiled via `osacompile` when available) which invokes:

```bash
python -m funcnodes standalone <file>
```

FuncNodes then tries to register the app with Launch Services (`lsregister`) and set defaults via `duti` if installed. If that fails, you can use Finder:

- Right click a `.fnw` → **Get Info** → **Open with** → choose the app → **Change All…**

______________________________________________________________________

## Security notes

- Treat `.fnw` files as potentially untrusted input: opening a workflow can trigger execution inside a worker.
- The registered launcher will execute Python code (`-m funcnodes`) when you double-click a `.fnw` file.
- If you move/remove the Python environment used at registration time, the launcher will break. Re-run `funcnodes standalone --register` to refresh it.

______________________________________________________________________

## Troubleshooting

### “Port already in use”

- Avoid forcing `--worker-port` / `--ui-port` unless you need fixed ports.
- Let standalone auto-pick ports when possible.

### “Worker already running / stale PID”

If a worker crashes and leaves stale files behind, check the workflow config directory:

- `<config_dir>/workers/worker_<uuid>.p`
- `<config_dir>/workers/worker_<uuid>.json`

If the PID is stale and no process is actually running, removing the PID file is usually safe.

### "Double-click doesn't open with FuncNodes"

- Windows: check Default apps settings for `.fnw`.
- Linux: run `xdg-mime query default application/x-funcnodes-fnw` and verify the `.desktop` entry exists.
- macOS: use Finder "Get Info → Open with → Change All…".

### "Debug logs"

To see detailed logs, run with `--debug`:

```bash
funcnodes standalone --debug ./workflow.fnw
```

______________________________________________________________________

## See also

- [CLI Reference](https://linkdlab.github.io/FuncNodes/v1.5.1/api/cli/index.md) — all FuncNodes commands
- [Workers](https://linkdlab.github.io/FuncNodes/v1.5.1/components/worker/index.md) — how workers execute workflows
- [Configuration](https://linkdlab.github.io/FuncNodes/v1.5.1/components/config/index.md) — global and worker configuration
- [Web UI Guide](https://linkdlab.github.io/FuncNodes/v1.5.1/ui-guide/react_flow/web-ui/index.md) — using the visual editor
