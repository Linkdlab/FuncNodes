from __future__ import annotations

import importlib
import sys
import types
from threading import RLock
from typing import Any, MutableMapping


class LazyImport(types.ModuleType):
    """
    A module-level proxy that defers importing a target module until first use.

    Typical usage
    -------------
    In a package's __init__.py (or any module):

        from typing import TYPE_CHECKING
        from funcnodes import LazyImport  # if you place this class in a local module

        if TYPE_CHECKING:
            import torch as torch  # makes type checkers & IDEs happy
        else:
            torch = LazyImport(
                local_name="torch",
                parent_module_globals=globals(),
                target="torch",
                install_hint="Install with: pip install torch",
                # register_in_sys_modules=True,  # optional: make `import torch` return the proxy
            )

        def infer(x):
            # First touch triggers import; subsequent calls are fast.
            return torch.tensor(x).sum()  # noqa: F821 (in runtime, `torch` is a module)

    Why this class?
    ---------------
    - You keep a single module-level binding (`torch`) that looks and behaves like
      the real module after the first use.
    - Startup stays fast because heavy dependencies are not imported until needed.
    - The first import is performed once per *process* and is thread-safe.
    - After loading, attribute access is as fast as a normal module attribute lookup.

    Parameters
    ----------
    local_name:
        The variable name you bind this proxy to inside the parent module (e.g., "torch").
        This is used to replace that binding with the real module after the first load.
    parent_module_globals:
        The dict returned by the calling module's `globals()`. Used to swap in the real module.
    target:
        Fully-qualified module path to import (e.g., "torch", "pkg.subpkg.mod").
    register_in_sys_modules:
        If True, installs the *proxy* object into `sys.modules[target]` during initialization,
        so that `import target` elsewhere in the process returns the proxy. The proxy is
        replaced with the real module on first load. Defaults to False to avoid global side
        effects unless explicitly requested.
    register_alias:
        If True, after loading the real module, register `sys.modules[local_name] = module`
        (rarely necessary; off by default to prevent surprising aliases).
    install_hint:
        Optional string appended to `ImportError` to help users install the missing dependency.

    Notes
    -----
    - The import happens on the thread that first touches the proxy. If you use this inside
      an event loop, consider offloading the *first* access to a thread/subprocess.
    - Caching is per process. A fresh subprocess will pay the one-time import cost again.
    """

    # Internal fields use a unique prefix to avoid collisions with real module attributes.
    _ll_local_name: str
    _ll_parent_globals: MutableMapping[str, Any]
    _ll_module: types.ModuleType | None
    _ll_lock: RLock
    _ll_register_in_sys_modules: bool
    _ll_register_alias: bool
    _ll_install_hint: str | None

    def __init__(
        self,
        local_name: str,
        parent_module_globals: MutableMapping[str, Any],
        target: str,
        *,
        register_in_sys_modules: bool = False,
        register_alias: bool = False,
        install_hint: str | None = None,
    ) -> None:
        super().__init__(target)

        self._ll_local_name = local_name
        self._ll_parent_globals = parent_module_globals
        self._ll_module = None
        self._ll_lock = RLock()
        self._ll_register_in_sys_modules = register_in_sys_modules
        self._ll_register_alias = register_alias
        self._ll_install_hint = install_hint

        # Minimal, nice metadata before load (helps repr() and tooling).
        pkg, _, _ = target.rpartition(".")
        self.__package__ = pkg or target
        self.__doc__ = (
            f"Lazy proxy for module '{target}'. Import deferred until first use."
        )

        if register_in_sys_modules:
            # Make `import target` return the proxy until the real module is loaded.
            # (Safe: setdefault avoids clobbering an already-imported real module.)
            sys.modules.setdefault(target, self)

    # ------------------------------- Public API --------------------------------

    def is_loaded(self) -> bool:
        """Return True if the target module has been imported in this process."""
        return self._ll_module is not None

    def load(self) -> types.ModuleType:
        """
        Import and return the real target module immediately.

        Equivalent to accessing any attribute for the first time, but explicit.
        Useful for warming caches or controlling when the first import occurs.
        """
        return self._load()

    # ------------------------------ Core loading --------------------------------

    def _load(self) -> types.ModuleType:
        """Internal: perform the one-time import in a thread-safe way."""
        with self._ll_lock:
            if self._ll_module is not None:
                return self._ll_module

            # If we registered the proxy under the target name, temporarily remove it so
            # importlib can perform a real import instead of returning the proxy.
            removed_proxy = False
            if (
                self._ll_register_in_sys_modules
                and sys.modules.get(self.__name__) is self
            ):
                removed_proxy = True
                del sys.modules[self.__name__]

            try:
                module = importlib.import_module(self.__name__)
            except Exception as exc:
                # Restore the proxy if we removed it, so subsequent attempts behave the same.
                if removed_proxy:
                    sys.modules[self.__name__] = self
                if isinstance(exc, ImportError) and self._ll_install_hint:
                    raise ImportError(
                        f"Failed to import '{self.__name__}'. {self._ll_install_hint}"
                    ) from exc
                raise
            else:
                # Cache the loaded module.
                self._ll_module = module

                # Re-register the real module for the target name if needed.
                if removed_proxy or self._ll_register_in_sys_modules:
                    sys.modules[self.__name__] = module

                # Optionally add an alias entry (rarely needed).
                if self._ll_register_alias and self._ll_local_name:
                    sys.modules.setdefault(self._ll_local_name, module)

                # Replace the binding in the parent module for future lookups.
                try:
                    self._ll_parent_globals[self._ll_local_name] = module
                except Exception:
                    # Parent might have been GC'ed or mutated; ignore.
                    pass

                # Make attribute access on this proxy as fast as the real module.
                # We *merge* dicts to keep our private _ll_* fields intact.
                self.__dict__.update(module.__dict__)

                # Keep helpful metadata for introspection/tools.
                self.__spec__ = getattr(module, "__spec__", None)
                self.__loader__ = getattr(module, "__loader__", None)
                self.__file__ = getattr(module, "__file__", None)
                self.__path__ = getattr(module, "__path__", None)  # type: ignore[attr-defined]
                self.__package__ = getattr(module, "__package__", self.__package__)
                self.__doc__ = getattr(module, "__doc__", self.__doc__)
                self.__wrapped__ = module  # convention used by inspect/typing tools

                return module

    # ---------------------------- Module interface ------------------------------

    def __getattr__(self, name: str) -> Any:  # noqa: D401 (trivial doc)
        """
        Resolve missing attributes.

        The first attribute access triggers the real import; subsequent
        accesses read directly from the real module.
        """
        module = self._load()
        return getattr(module, name)

    def __dir__(self) -> list[str]:
        # Provide sensible completion; import now so dir() shows real members.
        if self._ll_module is None:
            self._load()
        return sorted(self.__dict__.keys())

    def __repr__(self) -> str:
        if self._ll_module is None:
            return f"<LazyImport proxy for '{self.__name__}' (not loaded)>"
        return repr(self._ll_module)
