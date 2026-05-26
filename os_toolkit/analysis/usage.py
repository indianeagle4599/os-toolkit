"""
usage — disk usage tree analysis (single-root; dual-root planned).
"""

import os
import time
from typing import Dict, Optional

from os_toolkit.core.format import human_readable_size

_TREE_ASCII = str.maketrans({"└": "`", "├": "|", "│": "|", "─": "-"})


def _emit(line: str) -> None:
    """Print a tree line; fall back to ASCII connectors on narrow consoles."""
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.translate(_TREE_ASCII))


def get_total_size(path: str) -> int:
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_total_size(entry.path)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def scan_directory(
    path: str, max_depth: int, current_depth: int, verbosity: int, shallow_scan: bool
) -> Optional[Dict]:
    if current_depth > max_depth:
        return None

    if verbosity >= 2 or (verbosity == 1 and current_depth <= 1):
        if current_depth == 0:
            print(f"Scanning root: {path}")
        elif verbosity == 1 and current_depth == 1:
            print(f"Scanning: {path}")
        elif verbosity >= 2:
            print(f"{'  ' * current_depth}Scanning: {os.path.basename(path)}")

    result = {"path": path, "size": 0, "children": []}

    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        result["size"] += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        if current_depth + 1 <= max_depth:
                            child = scan_directory(
                                entry.path,
                                max_depth,
                                current_depth + 1,
                                verbosity,
                                shallow_scan,
                            )
                            if child:
                                result["children"].append(child)
                                result["size"] += child["size"]
                        else:
                            if not shallow_scan:
                                result["size"] += get_total_size(entry.path)
                except OSError:
                    continue
    except OSError as exc:
        if verbosity >= 2:
            print(f"Scan error: {exc}")
        return None

    if verbosity >= 2 or (verbosity == 1 and current_depth <= 1):
        if current_depth == 0:
            print(f"Completed root: {path} ({human_readable_size(result['size'])})")
        elif verbosity == 1 and current_depth == 1:
            print(f"Completed: {path} ({human_readable_size(result['size'])})")
        elif verbosity >= 2:
            print(
                f"{'  ' * current_depth}Completed: {os.path.basename(path)} "
                f"({human_readable_size(result['size'])})"
            )
    return result


def print_results(data: Dict, threshold: float, max_depth: int) -> None:
    output_data = []
    max_name_length = 0
    max_size_length = 0

    def prepare_output(item, depth=0, is_last=True, prefix=""):
        nonlocal max_name_length, max_size_length
        name = os.path.basename(item["path"])
        size = human_readable_size(item["size"])
        percentage = item["size"] / data["size"] * 100 if data["size"] else 0.0

        connector = "└─ " if is_last else "├─ "
        indent = prefix + connector

        max_name_length = max(max_name_length, len(indent + name))
        max_size_length = max(max_size_length, len(size))

        output_data.append(
            {
                "name": name,
                "size": size,
                "percentage": percentage,
                "indent": indent,
            }
        )

        if depth < max_depth:
            children = sorted(item["children"], key=lambda x: -x["size"])
            for i, child in enumerate(children):
                child_prefix = prefix + ("    " if is_last else "│   ")
                prepare_output(child, depth + 1, i == len(children) - 1, child_prefix)

    prepare_output(data)

    total_width = 110
    dot_length = total_width - max_name_length - max_size_length - 15

    for item in output_data:
        if item["percentage"] >= threshold:
            name_field = f"{item['indent']}{item['name']}"
            dots = "." * (max_name_length + dot_length - len(name_field))
            size_field = f"{item['size']:>{max_size_length}}"
            percentage_field = f"({item['percentage']:5.1f}%)"
            _emit(f"{name_field} {dots} {size_field} {percentage_field}")


def run_usage(
    path: str,
    max_depth: int,
    threshold: float,
    verbosity: int,
    shallow_scan: bool,
) -> bool:
    """Scan path and print usage tree. Returns True on success."""
    print(f"\nAnalyzing: {path}")
    start_time = time.time()
    scan_data = scan_directory(path, max_depth, 0, verbosity, shallow_scan)
    duration = time.time() - start_time

    if not scan_data:
        print("\nAnalysis failed - check path and permissions")
        return False

    print("\nStorage Analysis Results:")
    print_results(scan_data, threshold, max_depth)
    print(f"\nAnalysis completed in {duration:.2f} seconds")
    return True
