## Official Modules Overview

Use this page to discover what each packaged module adds to FuncNodes. Install modules from the UI (“Manage Libraries”) or via CLI `funcnodes modules install <name>`.

### Core utilities
- **funcnodes-basic** — typed input nodes, list/dict helpers with dynamic index/key options, logic/control utilities.
- **funcnodes-files** — sandboxed file/folder browsing, async downloads with progress, byte/file metadata types.
- **funcnodes-images** — unified image container (Pillow/NumPy backends), resize/crop/scale/show helpers.

### Data & numerics
- **funcnodes-numpy** — array creation/manipulation with dtype enums and serialization/rendering for previews.
- **funcnodes-pandas** — DataFrame/Series conversion, filtering, grouping, column/row selectors with dynamic dropdowns.

### Visualization
- **funcnodes-plotly** — figure/trace builders (express + graph_objects), color scales, layout utilities, image export.

### Vision & capture
- **funcnodes-opencv** — normalized float image ops: filtering, thresholding, morphology, drawing, transforms, segmentation.
- **funcnodes-webcam** — browser webcam capture into OpenCVImageFormat; device enumeration via React plugin.
- **funcnodes-yolo** — starter object-detection nodes (draft).

### Chemistry, spectra, optimization
- **funcnodes-rdkit** — molecule conversions (SMILES/InChI/molblock), SVG previews via custom encoders.
- **funcnodes-span** — spectroscopy: baseline estimation (multiple algorithms), smoothing, peak detection/fitting with Plotly plots.
- **funcnodes-lmfit** — model builders, auto-model selection, fitting, parameter sync, Plotly result plots.
- **funcnodes-bofire** — Bayesian optimization (create/tell/ask/predict) with separate-process options.
- **funcnodes-chromatography** — parse Shimadzu ASCII/LCD/QGD files into tidy DataFrames.
- **funcnodes-chemprop** — deep-learning molecular property prediction (data prep, training, async metrics).

### Tooling & testing
- **funcnodes-pytest** — pytest plugin (`@nodetest`, `all_nodes_tested`) for coverage and isolated test contexts.
- **funcnodes-module** — scaffolder/CLI to create/update modules with React plugin template.
- **funcnodes-repositories** — registry metadata and helpers to refresh available module versions.

### Packaging notes
- Every module is a standalone Python package with `[project.entry-points."funcnodes.module"]` advertising at least `module` and usually `shelf`; some add `react_plugin` or `external_worker`.
- Prefer aligning module versions with the installed `funcnodes`/`funcnodes-core` to avoid API drift.
- If running offline, mirror `funcnodes_repositories` and point the UI/CLI to your mirrored list.

## Module packaging essentials

1) **Entry points drive discovery**
Define the `funcnodes.module` entry points in `pyproject.toml`. Typical keys are:

- `module` → importable module root (required).
- `shelf` → exported `Shelf` object or dict (recommended for predictable grouping).
- `react_plugin` → optional React bundle entry for the editor host.
- `external_worker` → optional worker classes.

Example (from `funcnodes-files`):

```toml
[project.entry-points."funcnodes.module"]
module = "funcnodes_files"
shelf = "funcnodes_files:NODE_SHELF"
react_plugin = "funcnodes_files:REACT_PLUGIN"
```

2) **React plugin build target**
Module templates build the UI add-on as a library named `FuncNodesPlugin`, bundling `src/index.tsx` and marking `react`, `react-dom`, and `@linkdlab/funcnodes_react_flow` as externals (see `vite.config.ts` in `funcnodes_files`).

3) **Testing**
Use `pytest-funcnodes` decorators to isolate state and ensure shelf coverage; see the Testing section below.

## Testing FuncNodes modules

- Decorate node tests with `@pytest_funcnodes.nodetest` so registries are isolated and coverage is tracked.
- Use `pytest_funcnodes.all_nodes_tested(all_nodes, NODE_SHELF, ignore=...)` to assert every exported node is exercised.
- Run `pytest --nodetests-only` for a fast pass over node suites. The plugin also provides `@funcnodes_test` for runtime/integration checks.
