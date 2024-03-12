import os
import json
from .utils import deep_fill_dict

BASE_CONFIG_DIR = os.environ.get(
    "FUNCNODES_CONFIG_DIR", os.path.join(os.path.expanduser("~"), ".funcnodes")
)

DEFAULT_CONFIG = {
    "env_dir": os.path.join(BASE_CONFIG_DIR, "env"),
    "worker_manager": {
        "host": "localhost",
        "port": 9380,
    },
    "frontend": {
        "port": 8000,
    },
}


CONFIG = DEFAULT_CONFIG
CONFIG_DIR = BASE_CONFIG_DIR


def load_config(path):
    global CONFIG
    if not os.path.exists(path):
        config = DEFAULT_CONFIG
    else:
        with open(path, "r") as f:
            config = json.load(f)
    deep_fill_dict(config, DEFAULT_CONFIG)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    CONFIG = config


def check_config_dir():
    global CONFIG_DIR
    if not os.path.exists(BASE_CONFIG_DIR):
        os.makedirs(BASE_CONFIG_DIR)
    load_config(os.path.join(BASE_CONFIG_DIR, "config.json"))
    if "custom_config_dir" in CONFIG:
        load_config(os.path.join(CONFIG["custom_config_dir"], "config.json"))
        CONFIG_DIR = CONFIG["custom_config_dir"]


check_config_dir()
