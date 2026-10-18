"""Command-line interface for data_toolkit.

Subcommands:
    validate   run data-quality checks from a JSON config file
    profile    print/write a dataset profile
    report     run checks + profile and write a Markdown report

Exit codes: 0 = all checks passed, 1 = validation failures found,
2 = usage / I/O / config error.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from data_toolkit import DataValidator, Finding, profile, write_report

log = logging.getLogger("data_toolkit")

EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_ERROR = 2


def load_table(path: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    Lines starting with ``#`` in CSV files are treated as comments
    (handy for labelling synthetic/demo datasets inside the file).
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, comment="#")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"unsupported file type '{suffix}' (expected .csv, .xlsx, .xls)")


def load_config(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    if not isinstance(config, dict):
        raise ValueError("config file must contain a JSON object")
    return config


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        df = load_table(args.input)
        config = load_config(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        log.error("cannot load input/config: %s", exc)
        return EXIT_ERROR

    findings: List[Finding] = DataValidator(df).run_all(config)
    summary = DataValidator.summarize(findings)
    for f in findings:
        level = log.info if f["status"] == "pass" else log.warning
        level("[%s] %s on %s: %s", f["status"].upper(), f["check"], f["column"], f["details"])
    log.info(
        "validation complete: %d passed, %d failed",
        summary.get("pass", 0),
        summary.get("fail", 0),
    )
    if args.output:
        write_report(args.output, findings, profile(df), title="Validation Report", source=args.input)
        log.info("report written to %s", args.output)
    return EXIT_OK if summary.get("fail", 0) == 0 else EXIT_VALIDATION_FAILED


def cmd_profile(args: argparse.Namespace) -> int:
    try:
        df = load_table(args.input)
    except (OSError, ValueError) as exc:
        log.error("cannot load input: %s", exc)
        return EXIT_ERROR

    prof = profile(df)
    if args.json:
        print(json.dumps(prof, indent=2, default=str))
    else:
        log.info("rows=%d columns=%d duplicates=%d", prof["rows"], prof["columns"], prof["duplicate_rows"])
        for col in prof["column_names"]:
            log.info(
                "  %-20s %-10s nulls=%d (%.1f%%)",
                col,
                prof["dtypes"][col],
                prof["null_counts"][col],
                prof["null_ratios"][col] * 100,
            )
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    try:
        df = load_table(args.input)
        config = load_config(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        log.error("cannot load input/config: %s", exc)
        return EXIT_ERROR

    findings = DataValidator(df).run_all(config)
    write_report(args.output, findings, profile(df), title=args.title, source=args.input)
    summary = DataValidator.summarize(findings)
    log.info(
        "report written to %s (%d passed, %d failed)",
        args.output,
        summary.get("pass", 0),
        summary.get("fail", 0),
    )
    return EXIT_OK if summary.get("fail", 0) == 0 else EXIT_VALIDATION_FAILED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-toolkit",
        description="Automate data validation and reporting for CSV/Excel files.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="run data-quality checks")
    p_validate.add_argument("input", help="CSV or Excel file to validate")
    p_validate.add_argument("--config", required=True, help="JSON validation config")
    p_validate.add_argument("--output", help="optional Markdown report path")
    p_validate.set_defaults(func=cmd_validate)

    p_profile = sub.add_parser("profile", help="profile a dataset")
    p_profile.add_argument("input", help="CSV or Excel file to profile")
    p_profile.add_argument("--json", action="store_true", help="print profile as JSON")
    p_profile.set_defaults(func=cmd_profile)

    p_report = sub.add_parser("report", help="validate + profile into a Markdown report")
    p_report.add_argument("input", help="CSV or Excel file")
    p_report.add_argument("--config", required=True, help="JSON validation config")
    p_report.add_argument("--output", required=True, help="Markdown report path")
    p_report.add_argument("--title", default="Data Quality Report", help="report title")
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 — never crash with a traceback in CLI
        log.error("unexpected error: %s", exc)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
