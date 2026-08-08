import importlib
from typing import Any

def load_plugin_class(import_path: str) -> Any:
    """
    Given an import path string (e.g., 'agentforge_providers.google.GoogleProvider'),
    imports and returns the corresponding class.
    """
    parts = import_path.split(".")
    module_path = ".".join(parts[:-1])
    class_name = parts[-1]
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)
