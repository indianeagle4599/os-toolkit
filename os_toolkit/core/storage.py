"""
storage — filesystem path labels and transfer worker policy.

Feature: Product and benchmarks need rotational/physical-device facts and
         conservative worker caps on slow or unknown media.
Must do: describe_path, physical_id, effective_workers from src/dst paths.
Must NOT: Import benchmarks; require non-stdlib deps; probe beyond stat/sys/subprocess.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


@dataclass(frozen=True)
class WorkerDecision:
    """Result of effective_workers: pool size and optional clamp explanation."""

    requested: int
    effective: int
    reason: str  # empty when effective == requested (no clamp)


def _as_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def _probe_target(path: PathLike) -> Path:
    """Return nearest existing path for device probes (path itself or ancestor)."""
    p = _as_path(path).resolve()
    if p.exists():
        return p
    for parent in p.parents:
        if parent.exists():
            return parent
    return p.parent if p.parent != p else p


def _mount_for(path: str) -> str:
    path = os.path.abspath(path)
    if os.name == "nt":
        drive, _ = os.path.splitdrive(path)
        return drive or path[:1]
    return path


def _linux_physical_id(path: Path) -> Optional[str]:
    try:
        st = os.stat(path)
        major, minor = os.major(st.st_dev), os.minor(st.st_dev)
        block = f"/sys/dev/block/{major}:{minor}"
        if os.path.exists(block):
            name = os.path.basename(os.path.realpath(block))
            base = name.split(".")[0]
            return f"block:{base}"
        return f"stdev:{major}:{minor}"
    except OSError as exc:
        logger.debug("linux physical_id failed for %s: %s", path, exc)
        return None


def _windows_physical_id(mount: str) -> Optional[str]:
    letter = mount.rstrip("\\").rstrip(":")[:1]
    if not letter:
        return None
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Partition -DriveLetter '{letter}').DiskNumber",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        disk = (out.stdout or "").strip()
        if disk.isdigit():
            return f"disk:{disk}"
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("windows physical_id failed for %s: %s", mount, exc)
    return None


def _darwin_physical_id(path: Path) -> Optional[str]:
    try:
        st = os.stat(path)
        out = subprocess.run(
            ["diskutil", "info", "-plist", str(path)],
            capture_output=True,
            timeout=15,
            check=False,
        )
        if out.returncode == 0 and out.stdout:
            import plistlib

            data = plistlib.loads(out.stdout)
            parent = data.get("ParentWholeDisk") or data.get("DeviceIdentifier")
            if parent:
                return f"disk:{parent}"
        return f"stdev:{st.st_dev}"
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.debug("darwin physical_id failed for %s: %s", path, exc)
        try:
            return f"stdev:{os.stat(path).st_dev}"
        except OSError:
            return None


def physical_id(path: PathLike) -> Optional[str]:
    """Return a stable physical-device label for path, or None if unknown."""
    target = _probe_target(path)
    try:
        if platform.system() == "Darwin":
            return _darwin_physical_id(target)
        if os.name == "nt":
            return _windows_physical_id(_mount_for(str(target)))
        return _linux_physical_id(target)
    except OSError as exc:
        logger.debug("physical_id failed for %s: %s", path, exc)
        return None


def same_physical_device(path_a: PathLike, path_b: PathLike) -> Optional[bool]:
    """True if both paths share a physical device; None if either id is unknown."""
    a = physical_id(path_a)
    b = physical_id(path_b)
    if a is None or b is None:
        return None
    return a == b


def _linux_rotational(probe_path: Path) -> Optional[bool]:
    try:
        st = os.stat(probe_path)
        dev = os.path.basename(
            os.path.realpath(
                f"/sys/dev/block/{os.major(st.st_dev)}:{os.minor(st.st_dev)}"
            )
        )
        link = os.path.join("/sys/block", dev.split(".")[0], "rotational")
        if os.path.isfile(link):
            return open(link, encoding="ascii").read().strip() == "1"
    except OSError:
        pass
    return None


def _windows_rotational(mount: str) -> Optional[bool]:
    letter = mount.rstrip("\\").rstrip(":")[:1]
    if not letter:
        return None
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-PhysicalDisk | Where-Object {{$_.DeviceID -eq "
                f"(Get-Partition -DriveLetter '{letter}').DiskNumber}}).MediaType",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        text = (out.stdout or "").strip().lower()
        if "ssd" in text:
            return False
        if "hdd" in text:
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _darwin_rotational(path: Path) -> Optional[bool]:
    try:
        out = subprocess.run(
            [
                "diskutil",
                "info",
                "-plist",
                str(path),
            ],
            capture_output=True,
            timeout=15,
            check=False,
        )
        if out.returncode == 0 and out.stdout:
            import plistlib

            data = plistlib.loads(out.stdout)
            medium = str(data.get("MediumType") or data.get("IOContent") or "").lower()
            if "solid" in medium or "ssd" in medium:
                return False
            if "rotational" in medium or "hdd" in medium:
                return True
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return None


def _rotational_for_path(abs_path: str) -> Optional[bool]:
    """True=HDD, False=SSD, None=unknown."""
    mount = _mount_for(abs_path)
    probe = _probe_target(abs_path)
    if platform.system() == "Darwin":
        return _darwin_rotational(probe)
    if os.name == "nt":
        return _windows_rotational(mount)
    return _linux_rotational(probe)


def rotational_for_path(path: PathLike) -> Optional[bool]:
    """True=HDD, False=SSD, None=unknown. No physical_id probe."""
    return _rotational_for_path(os.path.abspath(os.fspath(path)))


def describe_path(path: str) -> dict[str, Any]:
    """
    Return device labels for a filesystem path.

    Keys: path (abs str), mount, rotational (True=HDD, False=SSD, None=unknown),
    platform, physical_id (stable str or None).
    """
    abs_path = os.path.abspath(path)
    mount = _mount_for(abs_path)
    rotational = _rotational_for_path(abs_path)
    return {
        "path": abs_path,
        "mount": mount,
        "rotational": rotational,
        "platform": platform.system(),
        "physical_id": physical_id(abs_path),
    }


def default_transfer_workers() -> int:
    """Default requested workers for parallel_copy (cpu_count // 2, at least 1)."""
    return max(1, multiprocessing.cpu_count() // 2)


# NOTE: effective_workers is NOT called by the production copy path.
# parallel_copy uses rotational_for_path only for routing.
# This function is retained for tests and potential future use.
def effective_workers(
    requested: int,
    src: PathLike,
    dst: PathLike,
    *,
    file_count: int,
    hdd_max: int = 1,
    unknown_max: int = 2,
    hdd_file_threshold: int = 50_000,
) -> WorkerDecision:
    """
    Compute safe worker count for parallel_copy from source/dest media and job size.

    Rules (in order; effective is always >= 1):
    1. SSD→SSD: min(requested, max(1, cpu_count // 2))
    2. Either side None: min(effective, unknown_max)
       Either side True (HDD): min(effective, 2)
    3. Dest True or None AND file_count > hdd_file_threshold: min(effective, hdd_max)
    """
    req = max(1, int(requested))
    effective = req

    src_rot = describe_path(str(src))["rotational"]
    dst_rot = describe_path(str(dst))["rotational"]

    if src_rot is False and dst_rot is False:
        effective = min(effective, default_transfer_workers())
    else:
        if src_rot is None or dst_rot is None:
            effective = min(effective, unknown_max)
        if src_rot is True or dst_rot is True:
            effective = min(effective, 2)
        if (dst_rot is True or dst_rot is None) and file_count > hdd_file_threshold:
            effective = min(effective, hdd_max)

    effective = max(1, effective)

    if effective == req:
        reason = ""
    elif (dst_rot is True or dst_rot is None) and file_count > hdd_file_threshold:
        reason = f"HDD dest, {file_count} files"
    elif src_rot is None or dst_rot is None:
        parts = []
        if src_rot is None:
            parts.append("unknown media (src)")
        if dst_rot is None:
            parts.append("unknown media (dst)")
        reason = "; ".join(parts)
    elif src_rot is True or dst_rot is True:
        if src_rot is True and dst_rot is True:
            reason = "HDD src and dest"
        elif src_rot is True:
            reason = "HDD src"
        else:
            reason = "HDD dest"
    else:
        reason = f"SSD cap ({effective}w)"

    return WorkerDecision(requested=req, effective=effective, reason=reason)
