window.noderenderer_worker = new SharedWorker(
  baseurl + "static/nodebuilder/pyodideSharedWorker.js",
  {
    type: "module",
  }
);

window.noderenderer_worker2 = new SharedWorker(
  baseurl + "static/nodebuilder/pyodideSharedWorker.js",
  {
    type: "module",
  }
);

const initalize_nodebuildernode = (node) => {
  if (!node.id) {
    console.error("NodeBuilder element does not have an id", node);
    return;
  }

  const codeSource = node.getAttribute("code-source");
  // male sure it has the "code-source" attribute
  if (!codeSource) {
    console.error(
      "NodeBuilder element does not have a code-source attribute",
      node
    );
    return;
  }

  let codenode;
  if (codeSource.startsWith("prev_")) {
    const classname = codeSource.replace("prev_", "");
    // find the closest previous node with the class name
    codenode = node.previousElementSibling;
    while (codenode && !codenode.classList.contains(classname)) {
      codenode = codenode.previousElementSibling;
    }

    if (!codenode || !codenode.classList.contains(classname)) {
      console.error(
        `NodeBuilder element does not have a previous sibling with class ${classname}`,
        node
      );
      return;
    }
  } else if (codeSource.startsWith("next_")) {
    const classname = codeSource.replace("next_", "");
    // find the closest next node with the class name
    codenode = node.nextElementSibling;
    while (codenode && !codenode.classList.contains(classname)) {
      codenode = codenode.nextElementSibling;
    }

    if (!codenode || !codenode.classList.contains(classname)) {
      console.error(
        `NodeBuilder element does not have a next sibling with class ${classname}`,
        node
      );
      return;
    }
  } else {
    codenode = document.getElementById(codeSource);
    if (!codenode) {
      console.error(
        `NodeBuilder element does not find an element with id ${codeSource}`,
        node
      );
      return;
    }
  }

  const pythonCode = codenode.textContent.trim(); // Extract Python code

  let height = node.getAttribute("nodebuilder-height") || "300px";
  let width = node.getAttribute("nodebuilder-width") || "300px";

  node.style.height = height;
  node.style.width = width;

  NodeBuilder(node, {
    python_code: pythonCode,
    show_python_editor: false,
    webworker: window.noderenderer_worker,
  });
};

const initializeNodeBuilders = () => {
  const allNodes = document.querySelectorAll(".nodebuilder");
  for (let i = 0; i < allNodes.length; i++) {
    const node = allNodes[i];
    initalize_nodebuildernode(node);
  }
};

window.addEventListener("hashchange", initializeNodeBuilders);

window.addEventListener("DOMContentLoaded", initializeNodeBuilders);

const nested_check_nodebuilder = (node) => {
  if (!node.classList) return check_children(node);
  if (!node.classList.contains("nodebuilder")) return check_children(node);
  if (node.children.length !== 0) return;
  initalize_nodebuildernode(node);
};

const check_children = (node) => {
  if (!node.children) return;
  if (node.children.length === 0) return;
  for (const child of node.children) {
    nested_check_nodebuilder(child);
  }
};

var observer = new MutationObserver(function (mutations) {
  mutations.forEach((mutation) => {
    if (mutation.addedNodes.length) {
      // Check for new code blocks and initialize them
      for (const node of mutation.addedNodes) {
        nested_check_nodebuilder(node);
      }
    }
  });
});

var config = { childList: true };

observer.observe(document.body, config);
