# Contributing to FuncNodes

Thanks for contributing! This repository is the main **FuncNodes** package (CLI + server + high-level API).

## Development setup (Python)

Prereqs:

- Python **3.11+**
- `uv` (https://github.com/astral-sh/uv)

Recommended environment variables (keeps caches/config local and out of `~/.funcnodes`):

- `UV_CACHE_DIR=.cache/uv`
- `FUNCNODES_CONFIG_DIR=.funcnodes`

Install dev dependencies:

```bash
cd FuncNodes
UV_CACHE_DIR=.cache/uv uv sync --group dev
```

Run tests:

```bash
cd FuncNodes
FUNCNODES_CONFIG_DIR=.funcnodes UV_CACHE_DIR=.cache/uv uv run pytest
```

## Code style

This repo uses **Ruff** (lint + format) and also runs **Flake8** via pre-commit.

Run locally:

```bash
cd FuncNodes
UV_CACHE_DIR=.cache/uv uv run pre-commit install
UV_CACHE_DIR=.cache/uv uv run pre-commit run -a
```

## TDD expectations

- Add/adjust tests **before** implementing behavior changes.
- Cover basic behavior and edge cases in separate tests.
- Avoid mocks unless you are simulating an external resource (APIs, long-running tasks, etc.).

## Docs (MkDocs)

Documentation lives in `FuncNodes/docs/content` and is built with MkDocs Material.

Install docs tooling:

```bash
cd FuncNodes
UV_CACHE_DIR=.cache/uv uv sync --group docs
```

Serve docs locally:

```bash
cd FuncNodes
UV_CACHE_DIR=.cache/uv uv run mkdocs serve -f docs/mkdocs.yml
```

## Pull requests

- Use a feature branch (pre-commit blocks direct commits to `main`/`master`/`test`).
- Include: what changed, why, how to test, and any screenshots for UI changes.
- Keep PRs focused; prefer small, reviewable changes.
