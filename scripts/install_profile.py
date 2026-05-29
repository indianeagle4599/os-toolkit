"""
install_profile — pip install helper for `just install PROFILE`.

Feature: Map install profiles to pip packages documented in requirements.txt.
Must do: Warn when ostk conda env is not active; install profile packages.
Must NOT: Parse requirements.txt; modify conda env definition.
"""

import os
import subprocess
import sys

_PROFILES = {
    "": [],
    "dev": ["pytest>=8.0", "black>=24.0"],
    "bench": ["requests>=2.31"],
    "ml": ["numpy>=1.26", "pandas>=2.0", "scikit-learn>=1.4", "tqdm>=4.66"],
    "all": [
        "pytest>=8.0",
        "black>=24.0",
        "requests>=2.31",
        "numpy>=1.26",
        "pandas>=2.0",
        "scikit-learn>=1.4",
        "tqdm>=4.66",
    ],
}


def main() -> int:
    profile = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if env != "ostk":
        print(f"WARNING: expected conda env ostk, got {env!r}", file=sys.stderr)

    pkgs = _PROFILES.get(profile)
    if pkgs is None:
        print(f"Unknown profile: {profile!r} (use dev|bench|ml|all)", file=sys.stderr)
        return 1
    if not pkgs:
        print("Runtime: stdlib only (nothing to install)")
        return 0

    print(f"Installing ({profile or 'default'}): {' '.join(pkgs)}")
    return subprocess.call([sys.executable, "-m", "pip", "install", *pkgs])


if __name__ == "__main__":
    raise SystemExit(main())
