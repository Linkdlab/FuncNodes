# FuncNodes Documentation 🚀

**FuncNodes** is a modular workflow automation system designed for **data processing, AI pipelines, task automation, and more**.

![example](./examples/titanic.png)
([Plotly](./examples/titanic.md) example of a FuncNodes workflow)

## 📌 Features

- **Node-based Execution** - Define workflows as interconnected nodes
- **Asynchronous Processing** - Handle tasks efficiently with async execution
- **Web-Based UI** - Manage workflows with a browser based No-Code interface
- **Integration-Friendly** - Connect to APIs, databases, and external services
- **Modular & Extensible** - Easily create and integrate custom nodes, e.g. via decorators:
<div>
<div id="node-code-demo" style="width:100%;aspect-ratio : 2 / 1;" ></div>
    <script>
(()=>{
if (window.inject_fn_on_div) inject_nodebuilder_into_div({
  id: document.getElementById("node-code-demo"),
  python_code: default_py_editor_code,
show_python_editor: true,
});
else
document.addEventListener("DOMContentLoaded", function (event) {
window.inject_nodebuilder_into_div({
  id: document.getElementById("node-code-demo"),
  python_code: default_py_editor_code,
show_python_editor: true,
});
});
})();
</script>

</div>

---

## 🔥 Getting Started

- **[Understanding FuncNodes](getting-started/introduction.md)** - Learn how FuncNodes processes workflows
- **[Installation Guide](getting-started/installation.md)** - Set up FuncNodes in your environment
- **[Using the UI](getting-started/basic_usage.md)** - Learn how to use the FuncNodes UI

---

## 🛠 Core Components

- **[Nodes](components/node.md)** - The building blocks of workflows
- **[Inputs & Outputs](components/inputs-outputs.md)** - Handling data flow between nodes

---

## 🎨 UI & Deployment

- **[Using the Web-Based UI](ui-guide/react_flow/web-ui.md)** - Visualize and control workflows

---

<!-- ## 🙌 Contributing

Want to help improve FuncNodes? Check out our **[Contribution Guide](contributing/setup.md)** for details on setting up a development environment, submitting pull requests, and testing your changes.

--- -->

💡 **Need Help?**

- Check the **[FAQ](faq/common-issues.md)**
- Report an issue on **[GitHub](https://github.com/Linkdlab/funcnodes/issues)**
- Join the community discussions on **[GitHub Discussions](https://github.com/Linkdlab/funcnodes/discussions)**

🚀 Happy automating with FuncNodes! 🎉
