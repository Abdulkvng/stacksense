"""Optional plugin loading for add-on packages."""

from functools import lru_cache
import importlib
import importlib.util
from types import ModuleType
from typing import Optional


def enterprise_available() -> bool:
    return importlib.util.find_spec("stacksense_enterprise") is not None


@lru_cache(maxsize=1)
def load_enterprise() -> Optional[ModuleType]:
    if not enterprise_available():
        return None
    return importlib.import_module("stacksense_enterprise")


@lru_cache(maxsize=1)
def load_enterprise_models() -> Optional[ModuleType]:
    if not enterprise_available():
        return None
    load_enterprise()
    return importlib.import_module("stacksense_enterprise.models")
