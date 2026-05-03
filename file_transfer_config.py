# file_transfer_config.py
# Default parameters for file_transfer_pro.py.
# CLI arguments always override these values.
#
# Usage: place this file in the same directory as file_transfer_pro.py,
# edit the values below, then run:
#   python file_transfer_pro.py
#
# To override a value at runtime:
#   python file_transfer_pro.py --source ./other --dest ./backup

# Required — leave empty ("") to require them via CLI every time.
SOURCE = ""  # source directory path
DEST = ""  # destination directory path

# Transfer behaviour
STRATEGY = "balanced"  # "smallest-first" | "largest-first" | "balanced"
WORKERS = (
    None  # None → CPU count // 2 (auto-detect); also used as ceiling for --adaptive
)
DRY_RUN = False  # True = simulate without copying any files
ADAPTIVE = True  # True = auto-tune worker count via timer-driven probing

# Output
# 0 = quiet (bar + summary only)
# 1 = normal (pre-scan + bar + summary)  ← default
# 2 = verbose (+ per-file error messages)
VERBOSITY = 1
