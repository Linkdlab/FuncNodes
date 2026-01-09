# React Plugin Development

FuncNodes modules can include React plugins to provide custom UI components — specialized input editors, output previews, and widgets that enhance the user experience for your node types.

______________________________________________________________________

## Overview

React plugins integrate with `@linkdlab/funcnodes_react_flow` (the FuncNodes UI host) and can provide:

- **Custom Previews** — Rich rendering of output values (charts, images, 3D views)
- **Custom Inputs** — Specialized editors (color pickers, molecule editors, file browsers)
- **Custom Widgets** — Additional UI for node headers or panels

```text
my_module/
├── src/funcnodes_mymodule/
│   ├── __init__.py
│   ├── nodes.py
│   └── _react_plugin.py    # Plugin info export
└── react_plugin/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        └── index.tsx       # Plugin implementation
```

______________________________________________________________________

## Quick Start

### 1. Scaffold with funcnodes_module

```bash
funcnodes_module create funcnodes_mymodule --with-react-plugin
```

This creates a complete React plugin scaffold ready to customize.

### 2. Manual Setup

Create the plugin directory:

```bash
mkdir -p react_plugin/src
cd react_plugin
```

Create `package.json`:

```json
{
  "name": "funcnodes-mymodule-react",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite build --watch",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@linkdlab/funcnodes_react_flow": "latest",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  },
  "peerDependencies": {
    "@linkdlab/funcnodes_react_flow": "*",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
```

Create `vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.tsx"),
      name: "FuncNodesPlugin",  // MUST be "FuncNodesPlugin"
      formats: ["es"],
      fileName: () => "funcnodes_mymodule_react.es.js"
    },
    rollupOptions: {
      external: [
        "react",
        "react-dom",
        "@linkdlab/funcnodes_react_flow"
      ],
      output: {
        globals: {
          react: "React",
          "react-dom": "ReactDOM",
          "@linkdlab/funcnodes_react_flow": "FuncNodesReactFlow"
        }
      }
    },
    outDir: "../src/funcnodes_mymodule/react_plugin"
  }
});
```

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

______________________________________________________________________

## Plugin Implementation

### Basic Plugin Structure

Create `src/index.tsx`:

```typescript
import React from "react";
import {
  FuncNodesReactPlugin,
  RenderNodeOutputProps,
  RenderNodeInputProps,
} from "@linkdlab/funcnodes_react_flow";

// Custom preview component
const MyTypePreview: React.FC<{ value: any }> = ({ value }) => {
  return (
    <div style={{ padding: 8, background: "#f0f0f0", borderRadius: 4 }}>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
};

// Custom input component
const MyTypeInput: React.FC<{
  value: any;
  onChange: (value: any) => void;
}> = ({ value, onChange }) => {
  return (
    <input
      type="text"
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: "100%" }}
    />
  );
};

// Plugin definition
const MyPlugin: FuncNodesReactPlugin = {
  // Render custom output previews
  renderNodeOutput: (props: RenderNodeOutputProps) => {
    const { type, value, fullscreen } = props;

    if (type === "MyCustomType") {
      return <MyTypePreview value={value} />;
    }

    // Return null to use default renderer
    return null;
  },

  // Render custom input editors
  renderNodeInput: (props: RenderNodeInputProps) => {
    const { type, value, onChange, render_options } = props;

    if (render_options?.type === "my_custom_input") {
      return <MyTypeInput value={value} onChange={onChange} />;
    }

    return null;
  },
};

// MUST export as default
export default MyPlugin;
```

### Register the Plugin in Python

Create `src/funcnodes_mymodule/_react_plugin.py`:

```python
from pathlib import Path

# Path to the built React plugin
REACT_PLUGIN = {
    "js": Path(__file__).parent / "react_plugin" / "funcnodes_mymodule_react.es.js",
}
```

Update `__init__.py`:

```python
from ._react_plugin import REACT_PLUGIN

__all__ = ["NODE_SHELF", "REACT_PLUGIN"]
```

Update `pyproject.toml` entry points:

```toml
[project.entry-points."funcnodes.module"]
module = "funcnodes_mymodule"
shelf = "funcnodes_mymodule:NODE_SHELF"
react_plugin = "funcnodes_mymodule:REACT_PLUGIN"
```

______________________________________________________________________

## Plugin API Reference

### FuncNodesReactPlugin Interface

```typescript
interface FuncNodesReactPlugin {
  // Render custom output previews
  renderNodeOutput?: (props: RenderNodeOutputProps) => React.ReactNode | null;

  // Render custom input editors
  renderNodeInput?: (props: RenderNodeInputProps) => React.ReactNode | null;

  // Render custom node header content
  renderNodeHeader?: (props: RenderNodeHeaderProps) => React.ReactNode | null;

  // Called when plugin is loaded
  onLoad?: () => void;

  // Called when plugin is unloaded
  onUnload?: () => void;
}
```

### RenderNodeOutputProps

```typescript
interface RenderNodeOutputProps {
  // The type string of the output
  type: string;

  // Current output value
  value: any;

  // Whether rendering in fullscreen/expanded mode
  fullscreen: boolean;

  // Node UUID
  nodeId: string;

  // Output ID
  outputId: string;

  // Render options from the node definition
  render_options?: Record<string, any>;
}
```

### RenderNodeInputProps

```typescript
interface RenderNodeInputProps {
  // The type string of the input
  type: string;

  // Current input value
  value: any;

  // Callback to update the value
  onChange: (value: any) => void;

  // Node UUID
  nodeId: string;

  // Input ID
  inputId: string;

  // Value constraints (min, max, options, etc.)
  value_options?: {
    min?: number;
    max?: number;
    step?: number;
    options?: string[] | { type: "enum"; keys: string[]; values: any[] };
  };

  // Render options from the node definition
  render_options?: Record<string, any>;

  // Whether input is disabled
  disabled?: boolean;
}
```

______________________________________________________________________

## Common Plugin Patterns

### Image Preview

```typescript
const ImagePreview: React.FC<{ value: any }> = ({ value }) => {
  if (!value) return null;

  // Assume value is base64 encoded image
  const src = `data:image/png;base64,${value}`;

  return (
    <img
      src={src}
      alt="Preview"
      style={{ maxWidth: "100%", maxHeight: 300 }}
    />
  );
};

const plugin: FuncNodesReactPlugin = {
  renderNodeOutput: (props) => {
    if (props.type === "ImageFormat" || props.type === "np.ndarray") {
      return <ImagePreview value={props.value} />;
    }
    return null;
  }
};
```

### Color Picker Input

```typescript
const ColorInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
}> = ({ value, onChange }) => {
  return (
    <input
      type="color"
      value={value || "#000000"}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: 40, height: 24, padding: 0, border: "none" }}
    />
  );
};

const plugin: FuncNodesReactPlugin = {
  renderNodeInput: (props) => {
    if (props.render_options?.type === "color") {
      return <ColorInput value={props.value} onChange={props.onChange} />;
    }
    return null;
  }
};
```

### Plotly Chart Preview

```typescript
import Plot from "react-plotly.js";

const PlotlyPreview: React.FC<{ value: any; fullscreen: boolean }> = ({
  value,
  fullscreen
}) => {
  if (!value) return null;

  const { data, layout } = value;

  return (
    <Plot
      data={data}
      layout={{
        ...layout,
        width: fullscreen ? 800 : 300,
        height: fullscreen ? 600 : 200,
        margin: { t: 20, r: 20, b: 30, l: 40 }
      }}
      config={{ displayModeBar: fullscreen }}
    />
  );
};
```

### Dropdown with Custom Styling

```typescript
const StyledDropdown: React.FC<{
  value: string;
  options: string[];
  onChange: (value: string) => void;
}> = ({ value, options, onChange }) => {
  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      style={{
        width: "100%",
        padding: "4px 8px",
        borderRadius: 4,
        border: "1px solid #ccc"
      }}
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
};
```

### File Upload Input

```typescript
const FileUploadInput: React.FC<{
  onChange: (file: File) => void;
}> = ({ onChange }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onChange(file);
    }
  };

  return (
    <input
      type="file"
      onChange={handleChange}
      style={{ width: "100%" }}
    />
  );
};
```

______________________________________________________________________

## Building and Deploying

### Development Build

```bash
cd react_plugin
npm install
npm run dev  # Watch mode
```

### Production Build

```bash
npm run build
```

The built file lands in `src/funcnodes_mymodule/react_plugin/`.

### Include in Package

Ensure the built JS file is included in your Python package:

```toml
# pyproject.toml
[tool.hatch.build.targets.wheel]
packages = ["src/funcnodes_mymodule"]

# Include the react_plugin directory
[tool.hatch.build.targets.wheel.force-include]
"src/funcnodes_mymodule/react_plugin" = "funcnodes_mymodule/react_plugin"
```

Or with setuptools:

```python
# setup.py or pyproject.toml
package_data = {
    "funcnodes_mymodule": ["react_plugin/*.js", "react_plugin/*.css"]
}
```

______________________________________________________________________

## Styling

### CSS Modules

```typescript
// styles.module.css
.preview {
  padding: 8px;
  border-radius: 4px;
  background: var(--fn-bg-secondary);
}

// index.tsx
import styles from "./styles.module.css";

const Preview = () => <div className={styles.preview}>...</div>;
```

### CSS-in-JS

```typescript
const Preview = () => (
  <div
    style={{
      padding: 8,
      borderRadius: 4,
      background: "var(--fn-bg-secondary)"
    }}
  >
    ...
  </div>
);
```

### FuncNodes CSS Variables

The host provides CSS variables for consistent theming:

| Variable              | Description          |
| --------------------- | -------------------- |
| `--fn-bg-primary`     | Primary background   |
| `--fn-bg-secondary`   | Secondary background |
| `--fn-text-primary`   | Primary text color   |
| `--fn-text-secondary` | Secondary text color |
| `--fn-accent`         | Accent color         |
| `--fn-border`         | Border color         |
| `--fn-radius`         | Border radius        |

______________________________________________________________________

## Debugging

### Development Tips

1. **Use React DevTools** — Install the browser extension
1. **Console logging** — `console.log()` in your plugin
1. **Hot reload** — Use `npm run dev` for watch mode
1. **Check Network tab** — Verify plugin JS is loaded

### Common Issues

**Plugin not loading:**

- Check entry point path in `pyproject.toml`
- Verify built JS file exists
- Check browser console for errors

**Component not rendering:**

- Verify type string matches exactly
- Check `renderNodeOutput` returns JSX, not null
- Ensure default export is the plugin object

**Styling issues:**

- Use CSS variables for theme consistency
- Avoid global styles that might conflict

______________________________________________________________________

## Examples from Official Modules

### funcnodes_plotly

Renders Plotly figures with zoom/pan controls:

```typescript
// Simplified example
const PlotlyPlugin: FuncNodesReactPlugin = {
  renderNodeOutput: (props) => {
    if (props.type === "plotly.graph_objs.Figure") {
      return <PlotlyRenderer figure={props.value} fullscreen={props.fullscreen} />;
    }
    return null;
  }
};
```

### funcnodes_files

File browser and upload widgets:

```typescript
const FilesPlugin: FuncNodesReactPlugin = {
  renderNodeInput: (props) => {
    if (props.render_options?.type === "file_browser") {
      return <FileBrowser onSelect={props.onChange} />;
    }
    return null;
  }
};
```

### funcnodes_rdkit

Molecule structure editor using JSME:

```typescript
const RDKitPlugin: FuncNodesReactPlugin = {
  renderNodeInput: (props) => {
    if (props.type === "Mol" && props.render_options?.editor) {
      return <MoleculeEditor smiles={props.value} onChange={props.onChange} />;
    }
    return null;
  },
  renderNodeOutput: (props) => {
    if (props.type === "Mol") {
      return <MoleculePreview smiles={props.value} />;
    }
    return null;
  }
};
```

______________________________________________________________________

## See Also

- [Writing Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/writing-modules/index.md) — Complete module guide
- [Testing Modules](https://linkdlab.github.io/FuncNodes/v1.5.1/extending/testing-modules/index.md) — Testing your module
- [Inputs & Outputs](https://linkdlab.github.io/FuncNodes/v1.5.1/components/inputs-outputs/index.md) — Render options reference
- [funcnodes_plotly](https://github.com/Linkdlab/funcnodes_plotly) — Example with React plugin
