# smart_zip_config.py
# Default parameters for smart_zip_pro.py.
# CLI arguments always override these values.
#
# Usage: place this file in the same directory as smart_zip_pro.py,
# edit the values below, then run:
#   python smart_zip_pro.py --root C:/Users/me/Archive

# Required unless provided by CLI.
ROOT = ""

# Output behavior
OUTPUT_DIR = ""
# Dry-run is the default mode.  --interactive prompts per candidate;
# --execute zips all candidates after a single confirmation.
DRY_RUN = False
INTERACTIVE = False
EXECUTE = False
OVERWRITE = False
RESUME = False
DELETE_ORIGINALS = False
WORKERS = 1

# Output
# 0 = quiet (recommendations + summary only)
# 1 = normal (scan progress + recommendations + summary)
# 2 = verbose (+ per-directory scan lines, scoring breakdown)
VERBOSITY = 1

# Sensitivity preset: "low", "normal", or "high".
SENSITIVITY = "normal"

# Folder names to skip entirely during the scan.
# Also settable via --exclude on the CLI (comma-separated).
EXCLUDE_NAMES = ()

# Folders that commonly create transfer/sync overhead from many files.
KNOWN_BAD_FOLDER_NAMES = (
    ".cache",
    ".git",
    ".gradle",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "bower_components",
    "cache",
    "node_modules",
    "site-packages",
    "vendor",
)

# Names that often indicate one logical dataset/corpus unit.
KNOWN_DATASET_FOLDER_NAMES = (
    "corpus",
    "corpora",
    "data",
    "dataset",
    "datasets",
    "images",
    "labels",
    "processed",
    "raw",
    "test",
    "train",
    "training",
    "val",
    "valid",
    "validation",
)

# Already-compressed/archive-like content should usually stay browseable as-is,
# unless file-count overhead is still the dominant problem.
ALREADY_COMPRESSED_EXTENSIONS = (
    ".7z",
    ".avi",
    ".bz2",
    ".flac",
    ".gz",
    ".lz4",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".rar",
    ".tar",
    ".tgz",
    ".webm",
    ".xz",
    ".zip",
    ".zst",
)

# Extensions that are often worth packing when they appear as many small files.
ZIP_FRIENDLY_EXTENSIONS = (
    ".cfg",
    ".css",
    ".csv",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".png",
    ".py",
    ".raw",
    ".rs",
    ".toml",
    ".ts",
    ".txt",
    ".wav",
    ".xml",
    ".yaml",
    ".yml",
)
