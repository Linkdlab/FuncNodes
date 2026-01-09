# Examples

Interactive examples demonstrating FuncNodes capabilities. Each example runs directly in your browser using Pyodide (Python compiled to WebAssembly).

Browser Execution

These examples run entirely in your browser. Initial load may take a few seconds as Python compiles to WebAssembly. Performance is slower than native Python installation.

______________________________________________________________________

## CSV Processing

**Modules used:** `funcnodes-files`, `funcnodes-pandas`

A data processing pipeline that:

- Reads CSV data from a file
- Performs basic data analysis
- Exports results to Excel format

**Key concepts:** File handling, DataFrame operations, data export

[**Open Example →**](https://linkdlab.github.io/FuncNodes/v1.5.1/examples/csv/index.md)

______________________________________________________________________

## Image Analysis

**Modules used:** `funcnodes-files`, `funcnodes-opencv`, `funcnodes-images`

A computer vision workflow demonstrating:

- Image loading and color space conversion
- Color-based region detection
- Image filtering and masking
- Live preview at each processing stage

**Key concepts:** OpenCV integration, live image previews, slider-based parameter tuning

[**Open Example →**](https://linkdlab.github.io/FuncNodes/v1.5.1/examples/cat/index.md)

______________________________________________________________________

## Plotly Visualization

**Modules used:** `funcnodes-files`, `funcnodes-pandas`, `funcnodes-plotly`

An interactive data visualization workflow:

- Load the Titanic dataset
- Clean and transform data
- Create interactive Plotly charts
- Analyze survival patterns by demographics

**Key concepts:** Plotly integration, DataFrame manipulation, interactive charts

[**Open Example →**](https://linkdlab.github.io/FuncNodes/v1.5.1/examples/titanic/index.md)

______________________________________________________________________

## Running Examples Locally

To run these examples in the full FuncNodes environment:

1. Start the UI: `funcnodes runserver`
1. Create or select a worker
1. Install required modules via **Manage Libraries**
1. Import the `.fnw` workflow file via **Nodespace** → **Import**

Example workflow files are bundled with the documentation.
