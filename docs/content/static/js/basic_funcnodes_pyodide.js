const baseurl = (window.__md_scope || {}).href || "/";
const default_py_editor_code = `# Edit me
import funcnodes as fn
@fn.NodeDecorator(node_id="my_node")
def my_node(input1: int, input2: int) -> int:
  return input1 + input2
`;

const divid_to_div_id = (div_or_id) => {
  let div, divid;
  if (typeof div_or_id === "string") {
    divid = div_or_id;
    div = document.getElementById(divid);
  } else {
    div = div_or_id;
    divid = div.getAttribute("id");
  }
  if (!div) {
    throw new Exception("div element does not exist for id", divid);
  }

  if (!divid) {
    throw new Exception("div element does not have an id", div);
  }
  return [div, divid];
};

window.active_workers = [];
window.webworkers = {};

window.inject_fn_on_div = ({ id, fnw_url, shared_worker = false }) => {
  const [div, divid] = divid_to_div_id(id);

  const workerurl =
    baseurl +
    (shared_worker
      ? "static/funcnodespyodide/pyodideSharedWorker.js"
      : "static/funcnodespyodide/pyodideDedicatedWorker.js");

  console.log("workerurl", shared_worker, workerurl);
  let webworker = window.webworkers[divid];
  if (webworker == undefined) {
    if (shared_worker) {
      webworker = new SharedWorker(workerurl, {
        type: "module",
        name: id,
      });
    } else {
      webworker = new Worker(workerurl, {
        type: "module",
        name: id,
      });
    }

    window.webworkers[id] = webworker;
  }
  const fnworker = new FuncNodes.FuncnodesPyodideWorker({
    // worker_url: workerurl,
    shared_worker: shared_worker,
    uuid: divid,
    // worker: webworker,
  });
  console.log("fnw_url", fnw_url);
  const fn = window.FuncNodes(div, {
    useWorkerManager: false,
    worker: fnworker,
    fnw_url: fnw_url,
  });

  window.active_workers.push(fnworker);
  const observer = new MutationObserver((mutationsList, observer) => {
    //check if the div is removed
    if (!document.getElementById(divid)) {
      observer.disconnect();
      fn.root.unmount();
      fnworker.stop();
      window.active_workers = window.active_workers.filter(
        (w) => w !== fnworker
      );
      return;
    }
  });
  observer.observe(document, { childList: true, subtree: true });
};

window.nodebuilderwebworkers = {};
window.inject_nodebuilder_into_div = ({
  id,
  shared_worker = true,
  worker_id = "nodbuilder_worker",
  show_python_editor = false,
  python_code = "",
}) => {
  const [div, divid] = divid_to_div_id(id);

  if (div.getAttribute("active") === "true") {
    return;
  }

  // set div attribute active to true
  div.setAttribute("active", "true");

  // const workerurl =
  //   baseurl +
  //   (shared_worker
  //     ? "static/nodebuilder/pyodideSharedWorker.js"
  //     : "static/nodebuilder/pyodideDedicatedWorker.js");

  // let webworker = window.nodebuilderwebworkers[worker_id];
  // if (webworker == undefined) {
  //   if (shared_worker) {
  //     webworker = new SharedWorker(workerurl, {
  //       type: "module",
  //       name: worker_id,
  //     });
  //   } else {
  //     webworker = new Worker(workerurl, {
  //       type: "module",
  //       name: worker_id,
  //     });
  //   }

  //   window.nodebuilderwebworkers[worker_id] = webworker;
  // }

  // const fnworker = new FuncNodes.FuncnodesPyodideWorker({
  //   // worker_url: workerurl,
  //   shared_worker: webworker instanceof SharedWorker,
  //   uuid: divid,
  //   worker: webworker,
  // });

  fn = NodeBuilder(div, {
    python_code: python_code,
    show_python_editor: show_python_editor,
  });

  const observer = new MutationObserver((mutationsList, observer) => {
    //check if the div is removed
    if (!document.getElementById(divid)) {
      observer.disconnect();
      fnworker.stop();
      fn.root.unmount();
      window.active_workers = window.active_workers.filter(
        (w) => w !== fnworker
      );
      //remove div attribute active
      div.removeAttribute("active");
      return;
    }
  });
  observer.observe(document, { childList: true, subtree: true });
};

const parse_nodebuildder_divs = () => {
  //get all divs with class nodebuilder
  const divs = document.querySelectorAll(".nodebuilder");
  //parse each div
  divs.forEach((div) => {
    //make sure div has an id
    if (!div.getAttribute("id")) {
      throw new Exception("div element does not have an id", div);
    }

    //get code from div
    let python_code;
    const python_code_src = div.getAttribute("code-source");
    if (python_code_src) {
      let codenode;
      if (python_code_src.startsWith("prev_")) {
        const identifiertoget = python_code_src.replace("prev_", "");
        codenode = div.previousElementSibling;
        while (codenode && !codenode.classList.contains(identifiertoget)) {
          codenode = codenode.previousElementSibling;
        }
        if (!codenode || !codenode.classList.contains(identifiertoget)) {
          console.error(
            `NodeBuilder element does not have a previous sibling with class ${identifiertoget}`,
            node
          );
          return;
        }
      } else if (python_code_src.startsWith("next_")) {
        const identifiertoget = python_code_src.replace("next_", "");
        codenode = div.nextElementSibling;
        while (codenode && !codenode.classList.contains(identifiertoget)) {
          codenode = codenode.nextElementSibling;
        }
        if (!codenode || !codenode.classList.contains(identifiertoget)) {
          console.error(
            `NodeBuilder element does not have a next sibling with class ${identifiertoget}`,
            node
          );
          return;
        }
      } else {
        console.log("python_code_src", python_code_src);
      }

      python_code = codenode.textContent.trim();
    }

    if (!python_code || python_code.trim() === "") {
      console.error("NodeBuilder element does not have a code-source", div);
      return;
    }

    let height = div.getAttribute("nodebuilder-height") || "300px";
    let width = div.getAttribute("nodebuilder-width") || "300px";

    div.style.height = height;
    div.style.width = width;

    worker_id = div.getAttribute("worker-id") || "code_nodbuilder_worker";
    inject_nodebuilder_into_div({
      id: div,
      python_code: python_code,
      show_python_editor: false,
      worker_id: worker_id,
    });
  });
};

const domoberserver = new MutationObserver((mutationsList, observer) => {});
domoberserver.observe(document, { childList: true, subtree: true });

document.addEventListener("DOMContentLoaded", function (event) {
  parse_nodebuildder_divs();
});
