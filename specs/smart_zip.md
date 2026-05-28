# Smart Zip Pro

## What it does

Scans a folder tree, scores directories as zip candidates, and prints recommendations. By default it does not create archives. Optional interactive mode prompts per candidate; optional execute mode confirms once then zips all candidates. Created zips can resume partial writes, overwrite existing archives when allowed, and optionally delete source folders only after a validated zip in the same run.

## Inputs

Required: root directory to scan.

Optional: output directory for zip files (must lie outside the root); sensitivity; exclude patterns; worker count; verbosity; dry-run; interactive; execute; overwrite; resume; delete-originals.

Optional defaults file `smart_zip_config.py`. CLI overrides config.

## Outputs

Mode banner; candidate list with scores and warnings; per-zip progress when creating; dry-run closing hint when no zip mode is selected. Validation and resume messages during execute paths.

## Guarantees

Default behavior is recommendation-only (no zip files) unless interactive or execute is set. Zip output path must not be inside the scan root. When delete-originals is enabled, deletion happens only after a successful zip validation in that run. Dry-run ignores resume, overwrite, and delete-originals with a warning.

## Known limits

Not a full backup or sync tool. Top-level multiprocessing applies to immediate subdirectories of the root only. Does not replace file transfer for bulk copy. Heavy optional dependencies are not required for scan and scoring.

## Adversarial surfaces

`.git` and `node_modules` heuristics; very large candidate folders; existing partial zip files; resume with mismatched file counts; files changing during scan; simultaneous interactive and execute flags; root redirected when pointed at `.git/objects`.
