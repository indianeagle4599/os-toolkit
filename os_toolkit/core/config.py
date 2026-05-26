"""
config — merge optional colocated *_config.py modules with CLI defaults.
"""

from types import ModuleType
from typing import Any, Optional


def cfg_get(config_module: Optional[ModuleType], attr: str, fallback: Any) -> Any:
    """
    Return config_module.attr when set and non-empty, else fallback.

    Matches the pattern used by root *_pro.py scripts: CLI args override
    config after parsing; this helper supplies defaults before argparse.
    """
    if config_module is None:
        return fallback
    value = getattr(config_module, attr, None)
    if value is not None and value != "":
        return value
    return fallback
