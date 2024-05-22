from typing import Dict, TypedDict, List
from .run import run_server


class ReactPlugin(TypedDict):
    """
    A typed dictionary for a React plugin.

    Attributes:
      js (list[str]): A list of JavaScript files.
    """

    js: list[str]


class ExpandedReactPlugin(TypedDict):
    """
    A typed dictionary for an expanded React plugin.

    Attributes:
      js (list[bytes]): A list of JavaScript files.
    """

    js: List[bytes]


FUNCNODES_REACT_PLUGIN: Dict[str, ReactPlugin] = {}


def add_react_plugin(name: str, plugin: ReactPlugin):
    """
    Add a React plugin to the FUNCNODES_REACT_PLUGIN dictionary.

    Args:
      name (str): The name of the plugin.
      plugin (ReactPlugin): The plugin to add.
    """
    FUNCNODES_REACT_PLUGIN[str(name)] = plugin


def get_react_plugin_content(key: str) -> ExpandedReactPlugin:
    """
    Get the content of a React plugin.

    Args:
      key (str): The key of the plugin.

    Returns:
      str: The content of the plugin.
    """
    key = str(key)
    resp: ExpandedReactPlugin = {"js": []}
    if "js" in FUNCNODES_REACT_PLUGIN[key]:
        resp["js"] = []
        for js in FUNCNODES_REACT_PLUGIN[key]["js"]:
            with open(js, "rb") as f:
                resp["js"].append(f.read())
    return resp
