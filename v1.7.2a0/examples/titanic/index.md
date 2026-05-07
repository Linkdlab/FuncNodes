# Titanic Survival Analysis (Plotly)

This example shows how to build an interactive survival analysis workflow using pandas + Plotly inside FuncNodes.

## What you’ll see

- CSV ingest with `funcnodes-files` + `funcnodes-pandas`
- Data wrangling (select/rename columns, handle missing values)
- Plotly express nodes to visualize survival by sex/class/age
- Live previews in the UI and an exportable figure

## How to run

1. Start the UI: `funcnodes runserver`
1. Create or select a worker.
1. Install required modules if not present: `funcnodes-files`, `funcnodes-pandas`, `funcnodes-plotly`.
1. Import the workflow:
1. Open **Nodespace → Import**, choose `titanic.fnw` (bundled with this example).
1. Drop in the sample Titanic CSV (any standard copy works) via the file upload node, or point to a local path under the worker `files/` directory.

## Tips

- Use the node previews to confirm each transformation before moving downstream.
- Plotly nodes clone the incoming figure by default; you can branch visualizations without side effects.
- To export the figure, connect `to_img` to `files.save` or use `figure.to_json` for downstream dashboards.
