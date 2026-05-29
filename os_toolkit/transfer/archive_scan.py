"""
archive_scan — filesystem scan, scoring, and recommendation display.
"""

import hashlib
import multiprocessing
import os
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from os_toolkit.core.config import cfg_get
from os_toolkit.core.format import human_readable_size
from os_toolkit.core.paths import extended_path, path_parts, rel_path

SENSITIVITY_PRESETS = {
    "low": {
        "min_files": 1000,
        "small_bytes": 500_000,
        "min_small_ratio": 0.80,
        "min_score": 70,
    },
    "normal": {
        "min_files": 500,
        "small_bytes": 1_000_000,
        "min_small_ratio": 0.70,
        "min_score": 60,
    },
    "high": {
        "min_files": 100,
        "small_bytes": 2_000_000,
        "min_small_ratio": 0.50,
        "min_score": 40,
    },
}


def normalize_exts(values):
    return {
        ext if ext.startswith(".") else f".{ext}"
        for ext in (str(value).strip().lower() for value in values)
        if ext
    }


def normalize_names(values):
    return {str(value).strip().lower() for value in values if str(value).strip()}


def base(path):
    return os.path.basename(path.rstrip(os.sep)).lower()


def is_inside_git(path):
    return ".git" in [part.lower() for part in path.replace("\\", "/").split("/")]


def is_descendant(path, parent):
    try:
        path = os.path.normcase(os.path.abspath(path))
        parent = os.path.normcase(os.path.abspath(parent))
        return path != parent and os.path.commonpath([path, parent]) == parent
    except ValueError:
        return False


def _path_parts_lower(rel: str) -> tuple:
    return tuple(p.lower() for p in path_parts(rel))


@dataclass
class Stat:
    path: str
    rel: str
    bytes: int = 0
    files: int = 0
    folders: int = 0
    direct_dirs: int = 0
    max_depth: int = 0
    small: int = 0
    compressed: int = 0
    symlinks: int = 0
    errors: list = field(default_factory=list)
    exts: Counter = field(default_factory=Counter)
    children: list = field(default_factory=list)

    @property
    def avg(self):
        return self.bytes / self.files if self.files else 0

    @property
    def small_ratio(self):
        return self.small / self.files if self.files else 0

    @property
    def compressed_ratio(self):
        return self.compressed / self.files if self.files else 0


@dataclass
class Candidate:
    stat: Stat
    zip_path: str
    score: int
    priority: int
    reasons: list
    warnings: list
    tags: set
    level: str = ""


def _resolve_threshold(cfg_name, preset_key, preset, config_module):
    raw = cfg_get(config_module, cfg_name, None)
    return raw if raw is not None else preset[preset_key]


def default_zip_output(root: str) -> str:
    """Sibling output directory outside the scan root when --output is omitted."""
    root_abs = os.path.abspath(root)
    base_name = os.path.basename(root_abs.rstrip(os.sep)) or "archive"
    parent = os.path.dirname(root_abs) or root_abs
    return os.path.join(parent, f"{base_name}_zips")


def settings(args, config_module=None):
    preset_name = args.sensitivity
    preset = SENSITIVITY_PRESETS[preset_name]
    root_abs = os.path.abspath(args.root)
    output = (
        os.path.abspath(args.output) if args.output else default_zip_output(root_abs)
    )
    return {
        "root": root_abs,
        "output": output,
        "interactive": args.interactive,
        "execute": args.execute,
        "overwrite": args.overwrite,
        "resume": args.resume,
        "delete_originals": args.delete_originals,
        "workers": args.workers,
        "verbosity": args.verbosity,
        "sensitivity": preset_name,
        "min_files": int(
            _resolve_threshold("MIN_FILES_FOR_ZIP", "min_files", preset, config_module)
        ),
        "small_bytes": int(
            _resolve_threshold(
                "SMALL_FILE_THRESHOLD_BYTES", "small_bytes", preset, config_module
            )
        ),
        "min_small_ratio": float(
            _resolve_threshold(
                "MIN_SMALL_FILE_RATIO", "min_small_ratio", preset, config_module
            )
        ),
        "min_score": int(
            _resolve_threshold("MIN_SCORE", "min_score", preset, config_module)
        ),
        "max_zip_bytes": int(cfg_get(config_module, "MAX_ZIP_SIZE_BYTES", 8 * 1024**3)),
        "exclude_names": normalize_names(
            args.exclude.split(",")
            if args.exclude
            else cfg_get(config_module, "EXCLUDE_NAMES", ())
        ),
        "bad_names": normalize_names(
            cfg_get(config_module, "KNOWN_BAD_FOLDER_NAMES", ())
        ),
        "dataset_names": normalize_names(
            cfg_get(config_module, "KNOWN_DATASET_FOLDER_NAMES", ())
        ),
        "compressed_exts": normalize_exts(
            cfg_get(config_module, "ALREADY_COMPRESSED_EXTENSIONS", ())
        ),
        "friendly_exts": normalize_exts(
            cfg_get(config_module, "ZIP_FRIENDLY_EXTENSIONS", ())
        ),
    }


# --- Scan ---


def add_file(stat, filename, size, cfg):
    ext = os.path.splitext(filename)[1].lower() or "[no_ext]"
    stat.files += 1
    stat.bytes += size
    stat.exts[ext] += 1
    stat.small += int(size <= cfg["small_bytes"])
    stat.compressed += int(ext in cfg["compressed_exts"])


def merge(parent, child):
    parent.children.append(child.path)
    parent.direct_dirs += 1
    parent.folders += child.folders + 1
    parent.files += child.files
    parent.bytes += child.bytes
    parent.small += child.small
    parent.compressed += child.compressed
    parent.symlinks += child.symlinks
    parent.errors.extend(child.errors[: max(0, 5 - len(parent.errors))])
    parent.exts.update(child.exts)
    parent.max_depth = max(parent.max_depth, child.max_depth + 1)


def scan_tree(path, root, cfg):
    found = {}
    stack = [path]
    pending_children = {}

    while stack:
        current = stack[-1]
        if current not in pending_children:
            stat = Stat(path=current, rel=rel_path(root, current))
            found[current] = stat
            child_dirs = []
            try:
                with os.scandir(extended_path(current)) as entries:
                    for entry in entries:
                        child = os.path.join(current, entry.name)
                        try:
                            if entry.is_symlink():
                                stat.symlinks += 1
                            elif entry.is_file(follow_symlinks=False):
                                size = entry.stat(follow_symlinks=False).st_size
                                add_file(stat, entry.name, size, cfg)
                            elif entry.is_dir(follow_symlinks=False):
                                if entry.name.lower() in cfg["exclude_names"]:
                                    continue
                                child_dirs.append(child)
                        except OSError as error:
                            if len(stat.errors) < 5:
                                stat.errors.append(f"{child}: {error}")
            except OSError as error:
                stat.errors.append(f"{current}: {error}")
            if cfg["verbosity"] >= 2:
                print(f"  scan: {stat.rel or '.'}")
            pending_children[current] = child_dirs
            stack.extend(child_dirs)
        else:
            stack.pop()
            stat = found[current]
            for child in pending_children.pop(current):
                if child in found:
                    merge(stat, found[child])

    return found


def scan_worker(args):
    path, root, cfg = args
    return path, scan_tree(path, root, cfg)


def scan_root(cfg):
    root = cfg["root"]
    root_stat = Stat(path=root, rel="")
    found = {}
    top_dirs = []
    if cfg["verbosity"]:
        print(f"\nScanning: {root}")
    try:
        with os.scandir(extended_path(root)) as entries:
            for entry in entries:
                path = os.path.join(root, entry.name)
                if entry.is_symlink():
                    root_stat.symlinks += 1
                elif entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    add_file(root_stat, entry.name, size, cfg)
                elif entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() not in cfg["exclude_names"]:
                        top_dirs.append(path)
    except OSError as error:
        root_stat.errors.append(f"{root}: {error}")

    use_pool = cfg["workers"] > 1 and len(top_dirs) > 1
    if use_pool and cfg["verbosity"]:
        print(
            f"Scanning {len(top_dirs):,} top-level folders with {cfg['workers']} workers"
        )
    if use_pool:
        tasks = [(path, root, cfg) for path in top_dirs]
        with multiprocessing.Pool(min(cfg["workers"], len(top_dirs))) as pool:
            for child_path, child_stats in pool.imap_unordered(scan_worker, tasks):
                merge(root_stat, child_stats[child_path])
                found.update(child_stats)
    else:
        for path in top_dirs:
            child_stats = scan_tree(path, root, cfg)
            merge(root_stat, child_stats[path])
            found.update(child_stats)

    found[root] = root_stat
    if cfg["verbosity"]:
        print(
            f"Scanned {len(found):,} folders, {root_stat.files:,} files "
            f"({human_readable_size(root_stat.bytes, extended_units=True)})"
        )
    return found


# --- Score ---


def child_names(stat):
    return {base(path) for path in stat.children}


def ext_share(stat, exts):
    return sum(stat.exts.get(ext, 0) for ext in exts) / stat.files if stat.files else 0


def top_ext_share(stat):
    return (
        stat.exts.most_common(1)[0][1] / stat.files if stat.files and stat.exts else 0
    )


def top_child_share(stat, stats):
    if not stat.files or not stat.children:
        return 0
    return max(stats[path].files for path in stat.children) / stat.files


def dataset_split(stat):
    names = child_names(stat)
    return bool(names & {"train", "training"}) and bool(
        names & {"test", "valid", "validation", "val", "dev"}
    )


def category_unit(stat, cfg):
    return (
        stat.direct_dirs >= 8
        and stat.files >= cfg["min_files"]
        and stat.small_ratio >= cfg["min_small_ratio"]
        and top_ext_share(stat) >= 0.50
    )


def broad_parent(stat, stats, logical):
    return (
        not logical
        and stat.direct_dirs >= 6
        and top_child_share(stat, stats) <= 0.55
        and top_ext_share(stat) < 0.65
    )


def planned_zip_path(path, root, output):
    if not output:
        output = default_zip_output(root)
    label = rel_path(root, path) or base(root) or "root"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
    safe = safe.replace("/", "__").replace("\\", "__").strip("._")[:140] or "folder"
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return os.path.join(output, f"{safe}--{digest}.zip")


def score(stat, stats, cfg):
    """Score a folder's zip-worthiness (0-100).

    A "normal" candidate — 500+ files, 70%+ small, zip-friendly extensions —
    lands around 62, just above the default MIN_SCORE of 60.  Known-unit
    folders (.git, node_modules, dataset splits) get priority bonuses that
    lift them above generic candidates.  Broad mixed parents and
    already-compressed folders get penalties that usually push them below the
    cutoff.
    """
    name = base(stat.path)
    if stat.files == 0:
        return None
    if is_inside_git(stat.path) and name != ".git":
        return None

    names = child_names(stat)
    tags, reasons, warnings = set(), [], []
    is_git = name == ".git"
    is_node = name == "node_modules"
    split = dataset_split(stat)
    corpus = category_unit(stat, cfg)
    known_unit = name in cfg["dataset_names"] or split or corpus or is_node or is_git
    known_bad = name in cfg["bad_names"]
    s = 0

    if stat.files >= cfg["min_files"]:
        s += 18
        reasons.append(f"{stat.files:,} files")
    else:
        s -= 25

    if stat.files >= cfg["min_files"] * 10:
        s += 14
        reasons.append("very high file count")
    elif stat.files >= cfg["min_files"] * 3:
        s += 8
        reasons.append("high file count")

    if stat.small_ratio >= cfg["min_small_ratio"]:
        s += 24
        reasons.append(f"{stat.small_ratio:.0%} small files")
    elif stat.small_ratio >= 0.50:
        s += 10
        reasons.append("many small files")
    else:
        s -= 18

    if 0 < stat.avg <= cfg["small_bytes"]:
        s += 10
        reasons.append("low average file size")
    if ext_share(stat, cfg["friendly_exts"]) >= 0.50:
        s += 10
        reasons.append("zip-friendly extension mix")

    if known_bad:
        s += 18
        reasons.append(f"known high-overhead folder: {name}")
    if is_node:
        s += 22
        tags.add("node_modules")
        reasons.append("dependency folder is its own transfer unit")
    if is_git:
        s += 24
        tags.add("git")
        reasons.append(".git is the complete Git metadata unit")
        warnings.append("for Git-only migration, git bundle/repack may be cleaner")
    if name in cfg["dataset_names"]:
        s += 8
        reasons.append("dataset/corpus-like folder name")
    if split:
        s += 24
        tags.add("dataset_split")
        reasons.append("train/test/validation children form one dataset")
    if corpus:
        s += 16
        tags.add("corpus")
        reasons.append("many similar child folders form one corpus")

    if ".git" in names and not is_git:
        s -= 30
        warnings.append("contains .git; recommend .git separately if needed")
    if broad_parent(stat, stats, known_unit):
        s -= 28
        tags.add("broad")
        warnings.append("broad mixed parent")
    if stat.compressed_ratio >= 0.80 and stat.avg > cfg["small_bytes"]:
        s -= 45
        warnings.append("mostly already-compressed large files")
    elif stat.compressed_ratio >= 0.60:
        s -= 20
        warnings.append("many files already compressed")
    if stat.bytes > cfg["max_zip_bytes"]:
        s -= 50
        warnings.append(
            f"over max zip size ({human_readable_size(cfg['max_zip_bytes'], extended_units=True)})"
        )

    s = max(0, min(100, int(s)))
    if s < cfg["min_score"]:
        return None
    if stat.files < cfg["min_files"] and not (known_bad or known_unit):
        return None

    priority = s
    priority += 20 if is_git or is_node or split else 0
    priority += 12 if corpus else 0
    priority -= 25 if "broad" in tags else 0
    return Candidate(
        stat=stat,
        zip_path=planned_zip_path(stat.path, cfg["root"], cfg["output"]),
        score=s,
        priority=priority,
        reasons=reasons,
        warnings=warnings,
        tags=tags,
    )


# --- Selection ---

LEVEL_REASONS = {
    "git": "Selected .git exactly; nested objects not recommended separately.",
    "node_modules": "Selected node_modules directly; project parent stays browseable.",
    "dataset_split": "Selected dataset root instead of separate split folders.",
    "corpus": "Selected corpus root to avoid many category-level zips.",
}


def level_reason(candidate, all_candidates):
    for tag, reason in LEVEL_REASONS.items():
        if tag in candidate.tags:
            return reason
    stat = candidate.stat
    if any(
        "broad" in c.tags
        for c in all_candidates
        if is_descendant(stat.path, c.stat.path)
    ):
        return "Selected this child because the parent is broad or mixed."
    if any(is_descendant(c.stat.path, stat.path) for c in all_candidates):
        return "Selected this parent because child candidates are one useful unit."
    return "Selected the smallest clear self-contained unit."


def choose_candidates(stats, cfg):
    candidates = [c for c in (score(s, stats, cfg) for s in stats.values()) if c]
    selected = []
    for candidate in sorted(
        candidates, key=lambda c: (-c.priority, -c.score, c.stat.rel)
    ):
        if not any(
            candidate.stat.path == ch.stat.path
            or is_descendant(candidate.stat.path, ch.stat.path)
            or is_descendant(ch.stat.path, candidate.stat.path)
            for ch in selected
        ):
            selected.append(candidate)
    for candidate in selected:
        candidate.level = level_reason(candidate, candidates)
    return _display_order(selected, stats, cfg["root"])


def _display_order(candidates, stats, root):
    by_path = {c.stat.path: c for c in candidates}
    ordered = []
    stack = [(root, False)]
    while stack:
        path, visited = stack.pop()
        stat = stats[path]
        if visited:
            if path in by_path:
                ordered.append(by_path[path])
            continue
        stack.append((path, True))
        children = sorted(
            stat.children, key=lambda p: _path_parts_lower(rel_path(root, p))
        )
        stack.extend((child, False) for child in reversed(children))
    seen = {c.stat.path for c in ordered}
    ordered.extend(c for c in candidates if c.stat.path not in seen)
    return ordered


# --- Display ---


def zip_non_dir_count(path, *, verify_crc=False):
    """Count non-directory zip entries; optionally run testzip() CRC check."""
    with zipfile.ZipFile(path, "r") as archive:
        count = sum(1 for info in archive.infolist() if not info.is_dir())
        bad = archive.testzip() if verify_crc else None
    return count, bad


def check_existing_zip(candidate):
    """Cheap existence + file-count check for display (no CRC verification)."""
    path = candidate.zip_path
    if not os.path.exists(path):
        return None
    try:
        archived, _ = zip_non_dir_count(path, verify_crc=False)
        return {"match": archived == candidate.stat.files, "archived": archived}
    except OSError:
        return {"match": False, "archived": 0}


def print_candidate(index, total, candidate):
    stat = candidate.stat
    top = ", ".join(f"{e} ({n:,})" for e, n in stat.exts.most_common(5)) or "-"
    print(f"\n[{index}/{total}] {stat.path}")
    print(f"    Zip      : {candidate.zip_path}")
    print(
        f"    Score    : {candidate.score}/100 | {stat.files:,} files | "
        f"{human_readable_size(stat.bytes, extended_units=True)} | avg "
        f"{human_readable_size(int(stat.avg), extended_units=True)}"
    )
    print(
        f"    Mix      : {stat.small_ratio:.0%} small | "
        f"{stat.compressed_ratio:.0%} compressed | {top}"
    )
    print(f"    Why      : {'; '.join(candidate.reasons)}")
    print(f"    Level    : {candidate.level}")
    if candidate.warnings:
        print(f"    Caution  : {'; '.join(candidate.warnings)}")
    existing = check_existing_zip(candidate)
    if existing:
        label = (
            "zip exists with expected file count; --resume can skip it."
            if existing["match"]
            else "zip exists but file count differs; --resume will rebuild it."
        )
        print(f"    Existing : {label}")
    if is_descendant(candidate.zip_path, candidate.stat.path):
        print(
            "    Caution  : zip path is inside the source folder and will be refused."
        )


def print_candidates(candidates):
    print("\nSmart zip recommendations")
    if not candidates:
        print("  No strong zip candidates found.")
        return
    for index, candidate in enumerate(candidates, 1):
        print_candidate(index, len(candidates), candidate)
