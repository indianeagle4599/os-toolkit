"""
Disk Analyzer Pro - Storage analysis tool with adaptive scanning
Features:
- Configurable through CLI, script parameters, and environment variables
- Adaptive verbosity and shallow scan options for faster analysis
- Accurate disk usage calculation
"""

import argparse
import os
import platform
import sys

from os_toolkit.analysis.usage import add_usage_arguments, run_usage
from os_toolkit.core.config import cfg_get

try:
    import disk_analyzer_config as _cfg
except ImportError:
    _cfg = None


DEFAULT_ROOT = os.path.abspath(os.sep) if platform.system() != "Windows" else "D:/"


def main():
    config = {
        "path": cfg_get(_cfg, "PATH", DEFAULT_ROOT),
        "max_depth": cfg_get(_cfg, "MAX_DEPTH", 7),
        "threshold": cfg_get(_cfg, "THRESHOLD", 1.0),
        "verbosity": cfg_get(_cfg, "VERBOSITY", 1),
        "shallow_scan": cfg_get(_cfg, "SHALLOW_SCAN", False),
    }

    parser = argparse.ArgumentParser(
        description="Disk Analyzer Pro - Adaptive storage analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python disk_analyzer_pro.py                   # Run with default settings
  python disk_analyzer_pro.py -p /home/user     # Analyze a specific directory
  python disk_analyzer_pro.py -d 3 -t 5         # Set max depth to 3 and threshold to 5%
  python disk_analyzer_pro.py -v 2 -s           # Run in verbose mode with shallow scan
        """,
    )
    add_usage_arguments(
        parser,
        path_default=config["path"],
        max_depth=config["max_depth"],
        threshold=config["threshold"],
        verbosity=config["verbosity"],
        shallow_scan=config["shallow_scan"],
    )
    args = parser.parse_args()

    ok = run_usage(
        args.path,
        args.max_depth,
        args.threshold,
        args.verbosity,
        args.shallow_scan,
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
