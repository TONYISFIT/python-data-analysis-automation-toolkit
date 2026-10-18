"""Render validation findings + dataset profile as a Markdown report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from data_toolkit.validators import Finding

_STATUS_ICON = {"pass": "✅", "fail": "❌"}


def render_markdown_report(
    findings: Sequence[Finding],
    profile: Dict[str, Any],
    title: str = "Data Quality Report",
    source: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> str:
    """Build a Markdown report string from findings and a profile dict."""
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_pass = sum(1 for f in findings if f["status"] == "pass")
    n_fail = sum(1 for f in findings if f["status"] == "fail")

    lines = [
        f"# {title}",
        "",
        f"_Generated: {ts}_",
    ]
    if source:
        lines.append(f"_Source: `{source}`_")
    lines += [
        "",
        "## Summary",
        "",
        f"- Checks run: **{len(findings)}**",
        f"- Passed: **{n_pass}** ✅",
        f"- Failed: **{n_fail}** ❌",
        "",
        "## Validation findings",
        "",
        "| Check | Column(s) | Status | Details |",
        "| --- | --- | --- | --- |",
    ]
    for f in findings:
        icon = _STATUS_ICON.get(f["status"], f["status"])
        lines.append(
            f"| `{f['check']}` | `{f['column']}` | {icon} {f['status']} | {f['details']} |"
        )

    lines += [
        "",
        "## Dataset profile",
        "",
        f"- Rows: **{profile.get('rows')}**, Columns: **{profile.get('columns')}**",
        f"- Duplicate rows: **{profile.get('duplicate_rows')}**",
        "",
        "### Columns",
        "",
        "| Column | dtype | nulls | null ratio |",
        "| --- | --- | --- | --- |",
    ]
    for col in profile.get("column_names", []):
        lines.append(
            f"| `{col}` | `{profile['dtypes'].get(col)}` "
            f"| {profile['null_counts'].get(col)} "
            f"| {profile['null_ratios'].get(col, 0.0):.1%} |"
        )

    numeric = profile.get("numeric_summary") or {}
    if numeric:
        lines += ["", "### Numeric summary", ""]
        stats = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
        lines.append("| Column | " + " | ".join(stats) + " |")
        lines.append("| --- | " + " | ".join(["---"] * len(stats)) + " |")
        for col, vals in numeric.items():
            row = " | ".join(
                f"{vals.get(s, float('nan')):,.2f}" for s in stats
            )
            lines.append(f"| `{col}` | {row} |")

    categorical = profile.get("categorical_top_values") or {}
    if categorical:
        lines += ["", "### Top categorical values", ""]
        for col, top in categorical.items():
            pairs = ", ".join(f"`{k}` ({v})" for k, v in top.items())
            lines.append(f"- `{col}`: {pairs}")

    lines.append("")
    return "\n".join(lines)


def write_report(
    path: str,
    findings: Sequence[Finding],
    profile: Dict[str, Any],
    **kwargs: Any,
) -> str:
    """Render and write the report to ``path``. Returns the path."""
    report = render_markdown_report(findings, profile, **kwargs)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report)
    return path
