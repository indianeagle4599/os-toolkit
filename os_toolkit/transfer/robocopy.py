"""
robocopy — optional Windows backend for large HDD directory copies.
"""

import os
import re
import shutil
import subprocess
from typing import Optional, Tuple

_ROBOCOPY = "robocopy"
_BYTE_SUFFIX = {
    "k": 1024,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
}


def robocopy_enabled() -> bool:
    """True when OS_TOOLKIT_ROBOCOPY=1 (opt-in only)."""
    return os.environ.get("OS_TOOLKIT_ROBOCOPY") == "1"


def robocopy_on_path() -> bool:
    return shutil.which(_ROBOCOPY) is not None


def should_use_robocopy(
    *,
    dst_rotational: Optional[bool],
    file_count: int,
    threshold: int,
    dry_run: bool,
    workers: int,
) -> bool:
    return (
        os.name == "nt"
        and robocopy_enabled()
        and (dst_rotational is True or dst_rotational is None)
        and file_count > threshold
        and not dry_run
        and workers == 1
    )


def _parse_size_token(token: str) -> int:
    token = token.replace(",", "").strip().lower()
    match = re.match(r"^([\d.]+)\s*([kmgt])?$", token)
    if not match:
        digits = re.sub(r"[^\d]", "", token)
        return int(digits) if digits else 0
    value = float(match.group(1))
    suffix = match.group(2) or ""
    return int(value * _BYTE_SUFFIX.get(suffix, 1))


def parse_robocopy_summary(output: str) -> Tuple[int, int]:
    """Return (files_copied, bytes_copied) from robocopy summary lines."""
    files_copied = 0
    bytes_copied = 0
    for line in output.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("files"):
            tail = stripped.split(":", 1)[-1].split()
            nums = [p for p in tail if re.match(r"^[\d,]+$", p)]
            if len(nums) >= 2:
                files_copied = int(nums[1].replace(",", ""))
        elif lower.startswith("bytes"):
            tail = stripped.split(":", 1)[-1].split()
            if len(tail) >= 2:
                bytes_copied = _parse_size_token(tail[1])
    return files_copied, bytes_copied


def run_robocopy_copy(src: str, dst: str) -> Tuple[int, str, int, int]:
    """
    Run robocopy /E /MT:1. Returns (exit_code, combined_output, files_copied, bytes_copied).
    """
    os.makedirs(dst, exist_ok=True)
    proc = subprocess.run(
        [
            _ROBOCOPY,
            src,
            dst,
            "/E",
            "/MT:1",
            "/R:1",
            "/W:1",
            "/NP",
            "/NFL",
            "/NDL",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    files_copied, bytes_copied = parse_robocopy_summary(combined)
    return proc.returncode, combined, files_copied, bytes_copied
