document.addEventListener("DOMContentLoaded", function () {
  document
    .querySelectorAll(".language-python.nodebuilder")
    .forEach((codeBlock) => {
      const pythonCode = codeBlock.textContent.trim(); // Extract Python code
      const wrapperDiv = document.createElement("div"); // Create container for NodeBuilder

      codeBlock.insertAdjacentElement("afterend", wrapperDiv);

      NodeBuilder(wrapperDiv, {
        python_code: pythonCode,
        show_python_editor: false,
      });
    });
});
