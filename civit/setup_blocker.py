"""
Setuptools and pkg_resources entry point blocker.

This module blocks problematic plugins from being loaded at the entry point level.
Run this before importing pytest to prevent plugin loading issues.

Example usage:
    import setup_blocker  # Must be first import
    import pytest
    # ... rest of your code
"""

import sys
import os
import importlib
from functools import wraps
from types import ModuleType


class BlockedModule(ModuleType):
    """A module that blocks imports related to problematic plugins."""

    def __init__(self, name):
        super().__init__(name)
        self._original_module = sys.modules.get(name)
        if self._original_module:
            # Copy all attributes from the original module
            for attr in dir(self._original_module):
                if not attr.startswith("__"):
                    setattr(self, attr, getattr(self._original_module, attr))

    def __getattr__(self, name):
        # Block any problematic attributes (plugins we want to disable)
        blocked_plugins = ["allure", "xdist", "cov"]
        if any(plugin in name.lower() for plugin in blocked_plugins):
            raise ImportError(f"Import of {name} is blocked")

        # Try to get the attribute from the original module
        if self._original_module and hasattr(self._original_module, name):
            attr = getattr(self._original_module, name)

            # If it's a function, wrap it to block problematic plugins
            if callable(attr) and not isinstance(attr, type):

                @wraps(attr)
                def wrapper(*args, **kwargs):
                    # Block any problematic arguments
                    for arg in args:
                        if isinstance(arg, str) and any(
                            plugin in arg.lower() for plugin in blocked_plugins
                        ):
                            return []  # Return empty list for entry points

                    for key, value in kwargs.items():
                        if isinstance(value, str) and any(
                            plugin in value.lower() for plugin in blocked_plugins
                        ):
                            kwargs[key] = None

                    return attr(*args, **kwargs)

                return wrapper
            return attr

        raise AttributeError(f"'{self.__name__}' has no attribute '{name}'")


# Create a list of modules to block/patch
modules_to_block = ["pkg_resources", "importlib.metadata", "setuptools"]

# Block all specified modules
for module_name in modules_to_block:
    if module_name in sys.modules:
        # Replace existing module with blocked version
        original_module = sys.modules[module_name]
        blocked_module = BlockedModule(module_name)
        sys.modules[module_name] = blocked_module
    else:
        # Preemptively block the module
        sys.modules[module_name] = BlockedModule(module_name)

print("Plugin entry points blocked")
