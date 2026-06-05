"""
devices — lean stdlib storage labels for benchmark result tagging.

Feature: Multi-drive benchmark results distinguish same-physical-device
         from cross-physical-device pairs.
Must do: Detect underlying physical device per path; return descriptive labels.
Must NOT: Hardcode device maps; require external dependencies; probe beyond stat/sys.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from os_toolkit.core.storage import (
    describe_path,
    physical_id,
    same_physical_device,
)

PathLike = Union[str, Path]


def device_tags(src: PathLike, dst: Optional[PathLike] = None) -> Dict[str, Any]:
    """Return JSONL device-tag dict for a src/dst pair (dst defaults to src)."""
    if dst is None:
        dst = src
    src_str, dst_str = str(src), str(dst)
    device_src = describe_path(src_str)
    device_dst = describe_path(dst_str)
    return {
        "device_src": device_src,
        "device_dst": device_dst,
        "physical_id_src": device_src.get("physical_id"),
        "physical_id_dst": device_dst.get("physical_id"),
        "same_physical_device": same_physical_device(src, dst),
    }
