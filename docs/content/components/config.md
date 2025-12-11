# Configuration

FuncNodes stores its configuration in `config.json` under the base directory (default `~/.funcnodes`). Override the base with `funcnodes --dir <path>` or by setting `FUNCNODES_CONFIG_DIR`.

## Structure (key sections)
- **env_dir** — base path for configs/logs/workers (usually the base dir itself).
- **worker_manager** — `host`, `port`, `ssl` for the Workermanager service.
- **frontend** — `host`, `port`, `ssl` for the UI server (`funcnodes runserver`).
- **nodes** — runtime defaults such as `pretrigger_delay` or test-mode flags.
- **logging** — handlers, log level, and format limits (see Logging section).
- **render_options** — global `typemap` and `inputconverter` hints for special types.

Defaults come from `DEFAULT_CONFIG` in `funcnodes_core.config`. On load, FuncNodes:
1) Ensures the config directory exists.
2) Reads `config.json` (or the `.bu` backup).
3) Fills missing keys from defaults, then writes back.

## Editing config
- Use any editor to adjust `~/.funcnodes/config.json`; restart UI/manager/workers to apply.
- CLI overrides: `funcnodes runserver --host ... --port ...` take precedence for that run.
- Environment: a `.env` file is loaded if present; env vars can override individual settings.

## Test mode
`funcnodes_core.config.set_in_test()` switches to a temporary config dir, disables file logging, promotes warnings to errors (optional), and is automatically used by `pytest_funcnodes` nodetests.

## Render options registry
`render_options` can be extended at runtime (e.g., by modules) via `fn.update_render_options`, normalizing type strings so the UI knows how to preview custom classes.
