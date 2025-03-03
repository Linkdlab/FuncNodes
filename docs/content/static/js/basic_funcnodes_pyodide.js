const baseurl = (window.__md_scope || {}).href || "/";

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

window.inject_fn_on_div = ({ id, fnw_url }) => {
  const [div, divid] = divid_to_div_id(id);

  const workerurl =
    baseurl + "static/funcnodespyodide/pyodideDedicatedWorker.js";
  const webworker =
    window.webworkers[divid] ||
    new Worker(workerurl, {
      type: "module",
      name: divid,
    });

  window.webworkers[divid] = webworker;

  const fnworker = new FuncNodes.FuncnodesPyodideWorker({
    worker_url: baseurl + "static/funcnodespyodide/pyodideDedicatedWorker.js",
    shared_worker: false,
    uuid: divid,
    worker: webworker,
  });

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
