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
WORKERS = (
    None  # None → CPU count // 2 (auto-detect)
)
HDD_MAX_WORKERS = 1
UNKNOWN_MEDIA_MAX_WORKERS = 2
HDD_FILE_COUNT_THRESHOLD = 50_000
# Set to 1 to enable robocopy backend on Windows HDD + large trees.
# Requires robocopy on PATH. Never enabled by default.
USE_ROBOCOPY_BACKEND = False  # overridden by OS_TOOLKIT_ROBOCOPY=1 env var
DRY_RUN = False  # True = simulate without copying any files

# Output
# 0 = quiet (bar + summary only)
# 1 = normal (pre-scan + bar + summary)  ← default
# 2 = verbose (+ per-file error messages)
VERBOSITY = 1
