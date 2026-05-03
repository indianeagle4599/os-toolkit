"""
Disk Analyzer Pro - Storage analysis tool with adaptive scanning
Features:
- Configurable through CLI, script parameters, and environment variables
- Adaptive verbosity and shallow scan options for faster analysis
- Accurate disk usage calculation
"""

import os
import argparse
import platform
import time
from typing import Dict, Optional

try:
    import disk_analyzer_config as _cfg
except ImportError:
    _cfg = None


def _cfg_get(attr: str, fallback):
    """Return value from config file if set, otherwise fallback."""
    if _cfg is not None:
        val = getattr(_cfg, attr, None)
        if val is not None and val != "":
            return val
    return fallback


DEFAULT_ROOT = os.path.abspath(os.sep) if platform.system() != "Windows" else "D:/"


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-friendly format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            break
        if unit != "TB":
            size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}"


def get_total_size(path: str) -> int:
    """Recursively calculate directory size"""
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
    """Recursive directory scanner with adaptive verbosity and accurate size calculation"""
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
                            if shallow_scan:
                                result[
                                    "size"
                                ] += 0  # Exclude deeper directories in shallow scan
                            else:
                                # For directories beyond max_depth, calculate total size without recursion
                                dir_size = get_total_size(entry.path)
                                result["size"] += dir_size
                except OSError:
                    continue

    except OSError as e:
        if verbosity >= 2:
            print(f"Scan error: {str(e)}")
        return None

    if verbosity >= 2 or (verbosity == 1 and current_depth <= 1):
        if current_depth == 0:
            print(f"Completed root: {path} ({human_readable_size(result['size'])})")
        elif verbosity == 1 and current_depth == 1:
            print(f"Completed: {path} ({human_readable_size(result['size'])})")
        elif verbosity >= 2:
            print(
                f"{'  ' * current_depth}Completed: {os.path.basename(path)} ({human_readable_size(result['size'])})"
            )
    return result


def print_results(data: Dict, threshold: float, max_depth: int):
    output_data = []
    max_name_length = 0
    max_size_length = 0

    def prepare_output(item, depth=0, is_last=True, prefix=""):
        nonlocal max_name_length, max_size_length
        name = os.path.basename(item["path"])
        size = human_readable_size(item["size"])
        percentage = item["size"] / data["size"] * 100

        connector = "└─ " if is_last else "├─ "
        indent = prefix + connector

        max_name_length = max(max_name_length, len(indent + name))
        max_size_length = max(max_size_length, len(size))

        output = {
            "name": name,
            "size": size,
            "percentage": percentage,
            "indent": indent,
            "children": [],
        }

        output_data.append(output)

        if depth < max_depth:
            children = sorted(item["children"], key=lambda x: -x["size"])
            for i, child in enumerate(children):
                child_prefix = prefix + ("    " if is_last else "│   ")
                prepare_output(child, depth + 1, i == len(children) - 1, child_prefix)

    prepare_output(data)

    # Set a fixed total width for the output
    total_width = 110  # You can adjust this value as needed

    # Calculate the length of the dot sequence
    dot_length = (
        total_width - max_name_length - max_size_length - 15
    )  # 15 is for spacing and percentage

    # Print the formatted output
    for item in output_data:
        if item["percentage"] >= threshold:
            name_field = f"{item['indent']}{item['name']}"
            dots = "." * (max_name_length + dot_length - len(name_field))
            size_field = f"{item['size']:>{max_size_length}}"
            percentage_field = f"({item['percentage']:5.1f}%)"
            print(f"{name_field} {dots} {size_field} {percentage_field}")


def main():
    """
    Main function to run the Disk Analyzer Pro.
    Handles command-line arguments, initiates the disk analysis, and displays results.
    """
    # Default configuration — values from disk_analyzer_config.py if present, else hardcoded
    config = {
        "path": _cfg_get("PATH", DEFAULT_ROOT),
        "max_depth": _cfg_get("MAX_DEPTH", 7),
        "threshold": _cfg_get("THRESHOLD", 1.0),
        "verbosity": _cfg_get("VERBOSITY", 1),
        "shallow_scan": _cfg_get("SHALLOW_SCAN", False),
    }

    # Set up command-line argument parser
    parser = argparse.ArgumentParser(
        description="Disk Analyzer Pro - Adaptive storage analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python disk_analyzer.py                   # Run with default settings
  python disk_analyzer.py -p /home/user     # Analyze a specific directory
  python disk_analyzer.py -d 3 -t 5         # Set max depth to 3 and threshold to 5%
  python disk_analyzer.py -v 2 -s           # Run in verbose mode with shallow scan
        """,
    )

    # Define command-line arguments
    parser.add_argument(
        "-p",
        "--path",
        default=config["path"],
        help="Root path to analyze (default: %(default)s)",
    )
    parser.add_argument(
        "-d",
        "--max-depth",
        type=int,
        default=config["max_depth"],
        help="Maximum depth for directory traversal (default: %(default)s)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=config["threshold"],
        help="Minimum percentage to display in results (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=config["verbosity"],
        help="Verbosity level: 0-quiet, 1-normal, 2-verbose (default: %(default)s)",
    )
    parser.add_argument(
        "-s",
        "--shallow-scan",
        action="store_true",
        default=config["shallow_scan"],
        help="Perform a shallow scan, skipping full size calculation for deeper directories",
    )

    # Parse command-line arguments
    args = parser.parse_args()

    # Update configuration with parsed arguments
    config.update(vars(args))

    print(f"\nAnalyzing: {config['path']}")
    start_time = time.time()

    # Perform directory scan
    scan_data = scan_directory(
        config["path"],
        config["max_depth"],
        0,  # Initial depth
        config["verbosity"],
        config["shallow_scan"],
    )

    duration = time.time() - start_time

    if scan_data:
        print("\nStorage Analysis Results:")
        print_results(scan_data, config["threshold"], config["max_depth"])
        print(f"\nAnalysis completed in {duration:.2f} seconds")
    else:
        print("\nAnalysis failed - check path and permissions")


if __name__ == "__main__":
    main()
