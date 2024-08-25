def get_installed_modules():
    import pkg_resources

    named_objects = {}
    for ep in pkg_resources.iter_entry_points(group="funcnodes.module"):
        if ep.module_name not in named_objects:
            named_objects[ep.module_name] = {}
        named_objects[ep.module_name][ep.name] = ep.load()

    return named_objects
