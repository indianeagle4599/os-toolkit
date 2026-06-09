"""
report — render committed benchmark summaries from aggregate JSON.

Feature: Patch RESULTS.md sections from {suite}_aggregate.json after orchestrator runs.
Must do: Reusable markdown helpers; suite-specific renderers; marker-based patch.
Must NOT: Assert pass/fail thresholds; fetch corpus; run benchmarks.
"""

from __future__ import annotations

import argparse
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from benchmarks.aggregate import load_aggregate

DEFAULT_RESULTS = Path(__file__).resolve().parent / "RESULTS.md"
SUITE_RENDERERS = ("analysis",)  # extend for transfer, zip


@dataclass(frozen=True)
class ToolRow:
    tool: str
    output: str = ""
    primary: bool = False

    def display_name(self) -> str:
        return f"**{self.tool}** (ours)" if self.primary else self.tool


ANALYSIS_TOOLS = (
    ToolRow("os_toolkit.usage", "usage tree", primary=True),
    ToolRow("stdlib.os.walk", "size total only"),
    ToolRow("stdlib.scandir", "size total only"),
)


# --- formatting (shared across suites) ---


def format_wall(sec: Optional[float]) -> str:
    if sec is None:
        return "—"
    if sec >= 1.0:
        return f"~{sec:.2f} s"
    return f"~{sec:.3f} s"


def format_throughput(bps: Optional[float]) -> str:
    if bps is None:
        return "—"
    mb = bps / (1024 * 1024)
    if mb >= 1024:
        return f"~{mb / 1024:.1f} GB/s"
    return f"~{mb:.0f} MB/s"


def short_signature(sig: object) -> str:
    if not isinstance(sig, str) or not sig:
        return "—"
    return f"{sig[:8]}…" if len(sig) > 8 else sig


def ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


# --- aggregate accessors (shared across suites) ---


def summaries_for_tool(payload: dict, tool: str) -> List[dict]:
    return [r for r in payload.get("summaries", []) if r.get("tool") == tool]


def tool_median(payload: dict, tool: str, field: str) -> Optional[float]:
    values = [
        r[f"{field}_median"]
        for r in summaries_for_tool(payload, tool)
        if r.get(f"{field}_median") is not None
    ]
    return statistics.median(values) if values else None


def scenario_ids(payload: dict) -> List[str]:
    return sorted({r["scenario_id"] for r in payload.get("summaries", [])})


def summary_row(payload: dict, scenario_id: str, tool: str) -> Optional[dict]:
    for row in payload.get("summaries", []):
        if row.get("scenario_id") == scenario_id and row.get("tool") == tool:
            return row
    return None


# --- markdown builders (shared across suites) ---


def md_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> List[str]:
    sep = "|" + "|".join("---" for _ in headers) + "|"
    lines = ["|" + "|".join(headers) + "|", sep]
    lines.extend("|" + "|".join(cells) + "|" for cells in rows)
    return lines


def section_markers(label: str) -> tuple[str, str]:
    return (f"<!-- bench:{label} -->", f"<!-- /bench:{label} -->")


def patch_results_md(
    results_path: Path,
    label: str,
    section_md: str,
    *,
    section_heading: str = "",
    insert_before: str = "## Transfer (copy)",
) -> None:
    begin, end = section_markers(label)
    block = f"{begin}\n{section_md.rstrip()}\n{end}\n"
    text = results_path.read_text(encoding="utf-8") if results_path.is_file() else ""

    if begin in text and end in text:
        pre, rest = text.split(begin, 1)
        _, post = rest.split(end, 1)
        results_path.write_text(
            pre.rstrip() + "\n\n" + block + post.lstrip("\n"), encoding="utf-8"
        )
        return

    if insert_before in text:
        pre, rest = text.split(insert_before, 1)
        prefix = pre.rstrip()
        if section_heading and section_heading not in prefix:
            prefix += f"\n\n{section_heading}\n\n"
        elif section_heading:
            prefix += "\n\n"
        results_path.write_text(
            prefix + block + "\n" + insert_before + rest, encoding="utf-8"
        )
        return

    results_path.write_text(
        (text.rstrip() + "\n\n" + block) if text else block, encoding="utf-8"
    )


def reproduce_command(suite: str, args: Any, results_dir: Path) -> str:
    """Rebuild a `just bench-multi` invocation from orchestrator args."""
    parts = [f"just bench-multi {suite}"]
    for label in ("a", "b", "c", "d"):
        val = getattr(args, f"drive_{label}", "") or ""
        if val:
            parts.append(f"--drive-{label} {val}")
    parts.append(f"--profile {args.profile}")
    if args.corpus:
        parts.append(f"--corpus {args.corpus}")
    parts.append(f"--scenarios {args.scenarios}")
    parts.append(f"--media-filter {args.media_filter}")
    parts.append(f"--results-dir {results_dir}")
    if getattr(args, "write_report", False):
        parts.append("--write-report")
        if args.report_label:
            parts.append(f"--report-label {args.report_label}")
        if args.corpus_note:
            parts.append(f'--corpus-note "{args.corpus_note}"')
    if getattr(args, "no_stage", False):
        parts.append("--no-stage")
    return " ".join(parts)


# --- suite: analysis ---


def _analysis_comparison_lines(
    ours_wall: Optional[float],
    walk_wall: Optional[float],
    scan_wall: Optional[float],
) -> List[str]:
    lines: List[str] = []
    vs_walk = ratio(walk_wall, ours_wall)
    if vs_walk:
        lines.append(
            f"**vs `os.walk`:** ~**{vs_walk:.1f}×** faster "
            f"({format_wall(ours_wall)} vs {format_wall(walk_wall)})."
        )
    vs_scan = ratio(ours_wall, scan_wall)
    if vs_scan is not None:
        pct = (vs_scan - 1.0) * 100
        if pct > 0:
            lines.append(
                f"**vs bare `scandir` sum:** ~**{pct:.0f}%** slower "
                f"({format_wall(ours_wall)} vs {format_wall(scan_wall)}) — "
                "full usage tree vs byte total only."
            )
        else:
            lines.append(
                f"**vs bare `scandir` sum:** within ~**{abs(pct):.0f}%** "
                f"({format_wall(ours_wall)} vs {format_wall(scan_wall)})."
            )
    return lines


def render_analysis_section(
    payload: dict,
    *,
    label: str,
    profile: str,
    command: str,
    corpus_note: str = "",
    tools: Sequence[ToolRow] = ANALYSIS_TOOLS,
) -> str:
    primary = next(t for t in tools if t.primary)
    medians = {
        t.tool: {
            "wall": tool_median(payload, t.tool, "wall_time_sec"),
            "bps": tool_median(payload, t.tool, "bytes_per_sec"),
        }
        for t in tools
    }

    lines = [
        f"### Disk usage · `{profile}` · {label}",
        "",
        f"**Status:** {'**complete**' if payload.get('pairs_satisfied') else 'incomplete'} "
        f"({payload.get('runs_attempted', '—')} orchestrator runs; "
        f"`pairs_satisfied: {payload.get('pairs_satisfied')}`).",
        f"**Corpus signature:** `{short_signature(payload.get('corpus_signature'))}`"
        + (f" — {corpus_note}" if corpus_note else ""),
        "",
        "**Tools:** `os_toolkit.usage` (`scandir` + usage tree) vs "
        "`os.walk` / recursive `scandir` size sums only.",
        "",
        "Command:",
        "",
        "```powershell",
        command.strip(),
        "```",
        "",
        "#### Rollup (median across scenarios)",
        "",
    ]
    lines.extend(
        md_table(
            ("Tool", "Median wall", "Median throughput", "Output"),
            (
                (
                    t.display_name(),
                    format_wall(medians[t.tool]["wall"]),
                    format_throughput(medians[t.tool]["bps"]),
                    t.output,
                )
                for t in tools
            ),
        )
    )
    lines.append("")
    walk_tool = next(t for t in tools if t.tool == "stdlib.os.walk")
    scan_tool = next(t for t in tools if t.tool == "stdlib.scandir")
    lines.extend(
        _analysis_comparison_lines(
            medians[primary.tool]["wall"],
            medians[walk_tool.tool]["wall"],
            medians[scan_tool.tool]["wall"],
        )
    )
    lines.extend(["", "#### Scenario detail", ""])
    detail_rows = []
    for sid in scenario_ids(payload):
        for t in tools:
            row = summary_row(payload, sid, t.tool)
            if not row:
                continue
            valid = f"{row.get('runs_valid', '—')}/{row.get('runs_total', '—')}"
            detail_rows.append(
                (
                    f"`{sid}`",
                    t.display_name(),
                    format_wall(row.get("wall_time_sec_median")),
                    format_throughput(row.get("bytes_per_sec_median")),
                    valid,
                )
            )
    lines.extend(
        md_table(
            ("Scenario", "Tool", "Median wall", "Median throughput", "Valid runs"),
            detail_rows,
        )
    )
    lines.append("")
    return "\n".join(lines)


# --- public API ---


def render_section(suite: str, payload: dict, **kwargs) -> str:
    if suite == "analysis":
        return render_analysis_section(payload, **kwargs)
    raise ValueError(f"no report renderer for suite {suite!r}; have: {SUITE_RENDERERS}")


def write_report(
    suite: str,
    aggregate_path: Path,
    *,
    label: str,
    results_path: Path = DEFAULT_RESULTS,
    section_heading: str = "## Disk usage (analysis)",
    **render_kwargs,
) -> Path:
    payload = load_aggregate(aggregate_path)
    section = render_section(suite, payload, label=label, **render_kwargs)
    patch_results_md(
        results_path,
        label,
        section,
        section_heading=section_heading,
    )
    return results_path


def write_suite_report(
    suite: str,
    aggregate_path: Path,
    args: Any,
    results_dir: Path,
    results_path: Path = DEFAULT_RESULTS,
) -> Optional[Path]:
    """Called by orchestrator when --write-report is set."""
    if not args.write_report or suite not in SUITE_RENDERERS:
        return None
    label = args.report_label or results_dir.name
    return write_report(
        suite,
        aggregate_path,
        label=label,
        profile=args.profile,
        command=reproduce_command(suite, args, results_dir),
        corpus_note=args.corpus_note or "",
        results_path=results_path,
    )


def infer_suite_from_aggregate(path: Path) -> str:
    stem = path.name.replace("_aggregate.json", "")
    if stem in SUITE_RENDERERS:
        return stem
    raise ValueError(f"cannot infer suite from {path.name}; pass --suite")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render benchmark section from aggregate JSON."
    )
    parser.add_argument("aggregate", type=Path, help="Path to *_aggregate.json")
    parser.add_argument("--suite", default="", choices=[""] + list(SUITE_RENDERERS))
    parser.add_argument("--label", required=True)
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument("--command", default="", help="Override reproduce command")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--corpus-note", default="")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    suite = args.suite or infer_suite_from_aggregate(args.aggregate)
    command = args.command or (
        f"just bench-multi {suite} --results-dir {args.aggregate.parent}"
    )
    out = write_report(
        suite,
        args.aggregate,
        label=args.label,
        profile=args.profile,
        command=command,
        corpus_note=args.corpus_note,
        results_path=args.results,
    )
    print(f"Updated {out} (bench:{args.label})", flush=True)


if __name__ == "__main__":
    main()
