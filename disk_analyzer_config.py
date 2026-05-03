# disk_analyzer_config.py
# Default parameters for disk_analyzer_pro.py.
# CLI arguments always override these values.
#
# Usage: place this file in the same directory as disk_analyzer_pro.py,
# edit the values below, then run:
#   python disk_analyzer_pro.py
#
# To override a value at runtime:
#   python disk_analyzer_pro.py -p C:/Users/me/Documents

# Target path — leave empty ("") to use the OS default root (C:/ on Windows, / on Linux/macOS).
PATH = ""

# Scan behaviour
MAX_DEPTH = 7  # maximum directory traversal depth
SHALLOW_SCAN = (
    False  # True = skip full size calculation for directories beyond max_depth
)
#        (faster but sizes at leaves will show as 0)

# Output filtering
THRESHOLD = 1.0  # minimum percentage to display (e.g. 1.0 hides anything < 1% of root)

# Output
# 0 = quiet (results only)
# 1 = normal (top-level scan progress)  ← default
# 2 = verbose (per-directory scan progress)
VERBOSITY = 1
