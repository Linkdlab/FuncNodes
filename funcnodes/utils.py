import csv
import requests
from funcnodes_core import AVAILABLE_MODULES, setup

AVAILABLE_REPOS = {}


def load_repo_csv():
    url = "https://raw.githubusercontent.com/Linkdlab/funcnodes_repositories/refs/heads/main/funcnodes_modules.csv"
    resp = requests.get(url, timeout=1)
    if resp.status_code != 200:
        return
    reader = csv.DictReader(resp.text.splitlines(), delimiter=",")
    for line in reader:
        AVAILABLE_REPOS[line["package_name"]] = line


def reload_base():
    setup()
    try:
        load_repo_csv()
    except Exception:
        pass
    for repo in AVAILABLE_REPOS.values():
        repo["installed"] = False

    for modulename, modueldata in AVAILABLE_MODULES.items():
        if modulename in AVAILABLE_REPOS:
            AVAILABLE_REPOS[modulename]["installed"] = True

        else:
            AVAILABLE_REPOS[modulename] = {
                "package_name": modulename,
                "installed": True,
                "summary": modueldata["description"],
            }


reload_base()
