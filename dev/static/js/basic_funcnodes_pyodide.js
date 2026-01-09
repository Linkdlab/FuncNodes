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
    throw new Error("div element does not exist for id: " + divid);
  }

  if (!divid) {
    throw new Error("div element does not have an id");
  }
  return [div, divid];
};

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

const fetch_fnw_url = async (fnw_url) => {
  if (!fnw_url) {
    return null;
  }
  if (fnw_url.length === 0) {
    return null;
  }
  let exportStr = null;
  try {
    const url = new URL(fnw_url, window.location.href).toString();
    console.log("preloading worker export from", url);
    const resp = await fetch(url);
    if (!resp.ok) {
      console.error(
        `Failed to load worker export (${resp.status}) from ${url}`
      );
    } else {
      const buf = await resp.arrayBuffer();
      const bytes = new Uint8Array(buf);
      const isZip = bytes[0] === 0x50 && bytes[1] === 0x4b; // "PK"

      exportStr = isZip
        ? arrayBufferToBase64(buf)
        : new TextDecoder().decode(bytes).trim();

      console.log("worker export loaded (chars)", exportStr.length);
    }
  } catch (e) {
    console.error("Failed to preload worker export from URL", e);
  }
  return exportStr;
};

window.inject_fn_on_div = async ({ id, fnw_url, shared_worker = false }) => {
  const [div, divid] = divid_to_div_id(id);

  console.log("fnw_url", fnw_url);
  let exportStr = await fetch_fnw_url(fnw_url);

  const fn = window.FuncNodes.FuncnodesPyodide(
    div,
    {
      shared_worker: shared_worker,
      uuid: divid,
      post_worker_initialized: async (worker) => {
        if (exportStr) {
          await worker.update_from_export(exportStr);
        }
      },
    },
    {
      // fnw_url: fnw_url,
    }
  );
};

// window.nodebuilderwebworkers = {};
// window.inject_nodebuilder_into_div = ({
//   id,
//   show_python_editor = false,
//   python_code = "",
// }) => {
//   const [div, divid] = divid_to_div_id(id);
//   div.classList.add("nodebuilder");
//   div.setAttribute("pycode", python_code);
//   if (window.nodebuilderwebworkers[divid]) {
//     return;
//   }

//   if (div.getAttribute("active") === "true") {
//     return;
//   }

//   // set div attribute active to true
//   div.setAttribute("active", "true");

//   const fn = NodeBuilder(div, {
//     python_code: python_code,
//     show_python_editor: show_python_editor,
//   });
//   console.log("fn", fn);
//   window.nodebuilderwebworkers[divid] = fn;
// };

// window.unmount = (id) => {
//   try {
//     const [div, divid] = divid_to_div_id(id);
//     console.log("unmounting", divid);
//     id = divid;
//     div.setAttribute("active", "false");
//   } catch (e) {}
//   console.log("disposing", id);
//   window.nodebuilderwebworkers[id].dispose();
//   delete window.nodebuilderwebworkers[id];
// };

// const parse_nodebuildder_divs = () => {
//   //get all divs with class nodebuilder
//   console.log("parse_nodebuildder_divs");
//   const divs = document.querySelectorAll(".nodebuilder");
//   const workers_to_remove = Object.keys(window.nodebuilderwebworkers);
//   //parse each div
//   divs.forEach((div) => {
//     //make sure div has an id
//     if (!div.getAttribute("id")) {
//       throw new Error("div element does not have an id", div);
//     }

//     //get code from div
//     let python_code = div.getAttribute("pycode");
//     const python_code_src = div.getAttribute("code-source");
//     if (python_code_src) {
//       let codenode;
//       if (python_code_src.startsWith("prev_")) {
//         const identifiertoget = python_code_src.replace("prev_", "");
//         codenode = div.previousElementSibling;
//         while (codenode && !codenode.classList.contains(identifiertoget)) {
//           codenode = codenode.previousElementSibling;
//         }
//         if (!codenode || !codenode.classList.contains(identifiertoget)) {
//           console.error(
//             `NodeBuilder element does not have a previous sibling with class ${identifiertoget}`,
//             node
//           );
//           return;
//         }
//       } else if (python_code_src.startsWith("next_")) {
//         const identifiertoget = python_code_src.replace("next_", "");
//         codenode = div.nextElementSibling;
//         while (codenode && !codenode.classList.contains(identifiertoget)) {
//           codenode = codenode.nextElementSibling;
//         }
//         if (!codenode || !codenode.classList.contains(identifiertoget)) {
//           console.error(
//             `NodeBuilder element does not have a next sibling with class ${identifiertoget}`,
//             node
//           );
//           return;
//         }
//       } else {
//         console.log("python_code_src", python_code_src);
//       }

//       python_code = codenode.textContent.trim();
//     }

//     if (!python_code || python_code.trim() === "") {
//       console.error("NodeBuilder element does not have a code-source", div);
//       return;
//     }

//     let height =
//       div.getAttribute("nodebuilder-height") || div.style.height || "300px";
//     let width =
//       div.getAttribute("nodebuilder-width") || div.style.width || "300px";

//     div.style.height = height;
//     div.style.width = width;

//     worker_id = div.getAttribute("worker-id") || "code_nodbuilder_worker";
//     inject_nodebuilder_into_div({
//       id: div,
//       python_code: python_code,
//       show_python_editor: false,
//       worker_id: worker_id,
//     });
//     workers_to_remove.splice(
//       workers_to_remove.indexOf(divid_to_div_id(div)[1]),
//       1
//     );
//   });
//   workers_to_remove.forEach((worker_id) => {
//     unmount(worker_id);
//   });
// };

// const domoberserver = new MutationObserver((mutationsList, observer) => {
//   parse_nodebuildder_divs();
// });
// domoberserver.observe(document, { childList: true, subtree: true });

// document.addEventListener("DOMContentLoaded", function (event) {
//   parse_nodebuildder_divs();
// });
