# Product specs (os-toolkit)

Plain-English contracts for root `*_pro.py` tools and their `os_toolkit/` implementations.

## Map

| Spec | Root entrypoints | Library module |
|------|------------------|----------------|
| [file_transfer.md](file_transfer.md) | `file_transfer_pro.py` | `os_toolkit.transfer.copy` |
| [usage.md](usage.md) | `disk_analyzer_pro.py`, `analyze_pro.py usage` | `os_toolkit.analysis.usage` |
| [smart_zip.md](smart_zip.md) | `smart_zip_pro.py` | `os_toolkit.transfer.archive` |
| [analyze_profile.md](analyze_profile.md) | *(internal to compare)* | `os_toolkit.analysis.profile` |
| [analyze_compare.md](analyze_compare.md) | `analyze_pro.py compare` | `os_toolkit.analysis.compare` |

## 2×2 analysis model

- **Usage (intra):** one root, tree output — `usage.md`.
- **Profile (intra):** internal pre-step for compare — `analyze_profile.md` (library only).
- **Compare (inter):** two directory roots — `analyze_compare.md`.

Workflow and agent doctrine live in `AGENTS.md` (not here).

## Spec evolution

Changing a documented guarantee requires updating the matching spec in the **same commit** as the code change.
