from typing import TypedDict
import os
import json
from .utils import deep_fill_dict

from dotenv import load_dotenv
from exposedfunctionality.function_parser.types import type_to_string

load_dotenv(override=True)


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
    """
    Loads the configuration file.

    Args:
      path (str): The path to the configuration file.

    Returns:
      None

    Examples:
      >>> load_config("config.json")
    """
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
    """
    Checks the configuration directory.

    Returns:
      None

    Examples:
      >>> check_config_dir()
    """
    global CONFIG_DIR
    if not os.path.exists(BASE_CONFIG_DIR):
        os.makedirs(BASE_CONFIG_DIR)
    load_config(os.path.join(BASE_CONFIG_DIR, "config.json"))
    if "custom_config_dir" in CONFIG:
        load_config(os.path.join(CONFIG["custom_config_dir"], "config.json"))
        CONFIG_DIR = CONFIG["custom_config_dir"]


check_config_dir()


class RenderOptions(TypedDict, total=False):
    """
    A typed dictionary for render options.

    Attributes:
      typemap (dict[str, str]): A dictionary mapping types to strings.
      inputconverter (dict[str, str]): A dictionary mapping input types to strings.
    """
    typemap: dict[str, str]
    inputconverter: dict[str, str]


FUNCNODES_RENDER_OPTIONS: RenderOptions = {"typemap": {}, "inputconverter": {}}


def update_render_options(options: RenderOptions):
    """
    Updates the render options.

    Args:
      options (RenderOptions): The render options to update.

    Returns:
      None

    Examples:
      >>> update_render_options({"typemap": {"int": "int32"}, "inputconverter": {"str": "string"}})
    """
    if not isinstance(options, dict):
        return
    if "typemap" not in options:
        options["typemap"] = {}
    for k, v in list(options["typemap"].items()):
        if not isinstance(k, str):
            del options["typemap"][k]
            k = type_to_string(k)
            options["typemap"][k] = v

        if not isinstance(v, str):
            v = type_to_string(v)
            options["typemap"][k] = v

    if "inputconverter" not in options:
        options["inputconverter"] = {}
    for k, v in list(options["inputconverter"].items()):
        if not isinstance(k, str):
            del options["typemap"][k]
            k = type_to_string(k)
            options["inputconverter"][k] = v
        if not isinstance(v, str):
            v = type_to_string(v)
            options["inputconverter"][k] = v
        FUNCNODES_RENDER_OPTIONS["inputconverter"][k] = v

    # make sure its json serializable
    try:
        json.dumps(options)
    except json.JSONDecodeError:
        return
    deep_fill_dict(
        FUNCNODES_RENDER_OPTIONS, options, merge_lists=True, unfify_lists=True
    )
