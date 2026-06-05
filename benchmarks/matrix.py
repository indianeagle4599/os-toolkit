"""
matrix — drive/scenario enumeration for multi-drive benchmarks.

Feature: Multi-drive benchmark CLIs need scenario enumeration from 1–4 drive paths.
Must do: Generate valid scenarios for drive count and filter mode; scratch helpers.
Must NOT: Execute scenarios; touch filesystem; import run_transfer or run_analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple

from os_toolkit.core.storage import describe_path, same_physical_device

_DRIVE_LABELS = ("a", "b", "c", "d")


@dataclass(frozen=True)
class Scenario:
    id: str
    src_drive: str
    dst_drive: str
    src_path: Path
    dst_path: Path


def parse_drives(args: Any) -> Dict[str, Path]:
    """Read --drive-a/b/c/d from an argparse namespace; return provided drives only."""
    drives: Dict[str, Path] = {}
    for label in _DRIVE_LABELS:
        value = getattr(args, f"drive_{label}", None)
        if value:
            drives[label] = Path(value)
    return drives


def add_drive_args(parser: Any) -> None:
    """Add --drive-a/b/c/d arguments to an argparse parser."""
    for label in _DRIVE_LABELS:
        parser.add_argument(f"--drive-{label}", dest=f"drive_{label}", default="")


def _all_pairs(keys: Sequence[str]) -> List[Tuple[str, str]]:
    return [(s, d) for s in keys for d in keys]


def _parse_custom(mode: str, valid_keys: Sequence[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    normalized = mode.replace("→", "->")
    for part in normalized.split(","):
        part = part.strip()
        if not part:
            continue
        if "->" not in part:
            raise ValueError(f"invalid custom scenario {part!r}; use src->dst")
        src, dst = (p.strip() for p in part.split("->", 1))
        if src not in valid_keys or dst not in valid_keys:
            raise ValueError(f"unknown drive in custom scenario {part!r}")
        pairs.append((src, dst))
    if not pairs:
        raise ValueError(f"no scenarios parsed from custom mode {mode!r}")
    return pairs


def _select_pairs(keys: Sequence[str], mode: str) -> List[Tuple[str, str]]:
    if not keys:
        return []
    if mode == "all":
        return _all_pairs(keys)
    if mode == "within":
        return [(k, k) for k in keys]
    if mode == "cross":
        return [(s, d) for s in keys for d in keys if s != d]
    if "->" in mode or "," in mode:
        return _parse_custom(mode, keys)
    raise ValueError(f"unknown scenario mode {mode!r}")


def scenario_weight(scenario: Scenario) -> int:
    """Lower weight runs earlier (lighter media / faster scenarios first)."""
    src_rot = describe_path(str(scenario.src_path))["rotational"]
    dst_rot = describe_path(str(scenario.dst_path))["rotational"]
    if src_rot is False and dst_rot is False:
        same = same_physical_device(str(scenario.src_path), str(scenario.dst_path))
        return 1 if same else 2
    if src_rot is False and dst_rot is not False:
        return 3
    if src_rot is not False and dst_rot is False:
        return 4
    same = same_physical_device(str(scenario.src_path), str(scenario.dst_path))
    return 6 if same else 5


def iter_transfer_scenarios(
    drives: Dict[str, Path], mode: str = "all"
) -> Iterator[Scenario]:
    """Yield copy scenarios (src drive → dst drive) for the given filter mode."""
    keys = list(drives.keys())
    scenarios = [
        Scenario(
            id=f"{src_k}_to_{dst_k}",
            src_drive=src_k,
            dst_drive=dst_k,
            src_path=drives[src_k],
            dst_path=drives[dst_k],
        )
        for src_k, dst_k in _select_pairs(keys, mode)
    ]
    scenarios.sort(key=scenario_weight)
    yield from scenarios


def iter_analysis_scenarios(
    drives: Dict[str, Path], mode: str = "all"
) -> Iterator[Scenario]:
    """Yield within-drive scan scenarios (N drives → N scenarios)."""
    if mode == "cross":
        raise ValueError("analysis benchmarks do not support cross-drive scenarios")
    if mode not in ("all", "within") and ("->" in mode or "," in mode):
        raise ValueError("analysis benchmarks do not support custom cross-drive modes")
    keys = list(drives.keys())
    scenarios = [
        Scenario(
            id=f"{key}_scan",
            src_drive=key,
            dst_drive=key,
            src_path=drives[key],
            dst_path=drives[key],
        )
        for key in keys
    ]
    scenarios.sort(key=scenario_weight)
    yield from scenarios


def scratch_paths(scenario: Scenario, timestamp: str) -> Tuple[Path, Path]:
    """Return (src_dir, dst_dir) corpus/dest trees for a transfer scenario."""
    base = f"bench_{timestamp}_{scenario.id}"
    src = scenario.src_path / base / "corpus"
    dst = scenario.dst_path / base / "dest"
    return (src, dst)


def analysis_corpus_path(scenario: Scenario, timestamp: str) -> Path:
    """Return corpus directory for a within-drive analysis scenario."""
    return scenario.src_path / f"bench_{timestamp}_{scenario.id}" / "corpus"
