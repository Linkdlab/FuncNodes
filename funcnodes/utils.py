"""
utils used in the project
"""
from __future__ import annotations
from typing import List, Any, Dict

# callable type which takes *args and **kwargs but requires the src kwarg:
# EventCallback = Callable[]


def flatten_object(obj: dict):
    # gets a array off deep obecjt kezs
    # and returns a flat object
    leafs = []
    branches = []
    for key in obj:
        subbranch = [key]
        if isinstance(obj[key], dict):
            subleafs, subbranches = flatten_object(obj[key])
            leafs.extend(subleafs)
            branches.extend([subbranch + branch for branch in subbranches])
        else:
            leafs.append(obj[key])
            branches.append(subbranch)
    return leafs, branches


def _dict_list_value_flatten(
    lst: List[Any], key: str, separator="__"
) -> Dict[str, Any]:
    """Flattens a list to a dict with the key as prefix and the index as suffix

    Parameters
    ----------
    l : List[Any]
        The list to be flattened
    key : str
        The key to be used as prefix
    separator : str, optional
        The separator to be used between key and index, by default "__"

    Returns
    -------

        The flattened dict
    """
    flat_dict = {}
    for i, v in enumerate(lst):
        if isinstance(v, dict):
            subdict = flatten_dict(v, separator)
            for subkey, subitem in subdict.items():
                flat_dict[key + separator + str(i) + separator + subkey] = subitem
        elif isinstance(v, list):
            flat_dict.update(
                _dict_list_value_flatten(
                    v, key + separator + str(i), separator=separator
                )
            )
        else:
            flat_dict[key + separator + str(i)] = v
    return flat_dict


def flatten_dict(d: Dict[str, Any], separator="__", flat_arrays=True) -> Dict[str, Any]:
    """Flattens a dict recursively

    Parameters
    ----------
    d : Dict[str, Any]
        The dict to be flattened
    separator : str, optional
        The separator to be used between the kezs and the subkeys, by default "__"
    flat_arrays : bool, optional
        If true, arrays will be flattened, by default True

    Returns
    -------
    Dict[str, Any]
        The flattened dict

    """

    flat_dict: Dict[str, Any] = {}
    for key in d:
        if isinstance(d[key], dict):
            subdict = flatten_dict(d[key], separator)
            for subkey, subval in subdict.items():
                flat_dict[key + separator + subkey] = subval
        elif isinstance(d[key], list) and flat_arrays:
            flat_dict.update(_dict_list_value_flatten(d[key], key, separator=separator))

        else:
            flat_dict[key] = d[key]

    return flat_dict


def deep_fill_dict(
    target_dict: Dict[Any, Any], source_dict: dict, overwrite_existing: bool = False
) -> Dict[Any, Any]:
    """
    deep_fill_dict
    A target dict is filled with the values of a source dict recursively
    if the key does not exist in the target dict

    Parameters
    ----------
    target_dict : Dict[Any, Any]
        The dict to be filled
    source_dict : dict
        The dict to be used as a source
    overwrite_existing : bool, optional
        If true, existing values in the target dict will be overwritten, by default False

    Returns
    -------
    Dict[Any, Any]
        The filled dict
    """
    for key, value in source_dict.items():
        if isinstance(value, dict):
            # get node or create one
            if key not in target_dict:
                target_dict[key] = dict()
            if isinstance(target_dict[key], dict):
                node: dict = target_dict[key]
                deep_fill_dict(
                    node,
                    value,
                    overwrite_existing,
                )
                continue
        if overwrite_existing or (key not in target_dict):
            target_dict[key] = value

    return target_dict


def deep_remove_dict_on_equal(target_dict: dict, remove_dict: dict) -> Dict[Any, Any]:
    """
    deep_remove_dict_on_equal
    All keys in a dict that have the same value as the value of the key
    in theremove dict are removed

    Parameters
    ----------
    target_dict : dict
        The dict to be cleaned
    remove_dict : dict
        The dict to be used as a source

    Returns
    -------
    Dict[Any, Any]
        The cleaned dict
    """
    for key, value in remove_dict.items():
        if key in target_dict:
            if isinstance(value, dict):
                if isinstance(target_dict[key], dict):
                    node: dict = target_dict[key]
                    deep_remove_dict_on_equal(node, value)
                    continue
            if target_dict[key] == value:
                del target_dict[key]

    return target_dict
