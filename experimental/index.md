# Experimental

Experimental features

Pages in this section describe features that are **new**, **evolving**, or **platform-dependent**. Expect rough edges and occasional breaking changes between releases.

## What "experimental" means

- CLI flags and behavior may change without a long deprecation window.
- OS integration (file associations, icons) depends on the underlying desktop/OS and may require manual steps.
- If something behaves unexpectedly, please report it with your OS, FuncNodes version, and exact command line.

______________________________________________________________________

## Available experimental features

| Feature                                                                             | Description                                                 | Status                    |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------- |
| [Standalone](https://linkdlab.github.io/FuncNodes/experimental/standalone/index.md) | Open a single `.fnw` workflow with its own dedicated worker | Stable for day-to-day use |

______________________________________________________________________

## Standalone mode (quick start)

Open any `.fnw` file directly:

```bash
funcnodes standalone path/to/workflow.fnw
```

Register `.fnw` files to open with FuncNodes (OS file association):

```bash
funcnodes standalone --register
```

→ See [Standalone](https://linkdlab.github.io/FuncNodes/experimental/standalone/index.md) for full documentation.
