"""End-to-end demo: validate the synthetic sample data and write a Markdown report.

Run from the repo root:
    python example/usage.py
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_toolkit import DataValidator, profile, write_report  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("demo")

EXAMPLE = Path(__file__).resolve().parent


def main() -> int:
    df = pd.read_csv(EXAMPLE / "sample_data.csv", comment="#")
    config = json.loads((EXAMPLE / "validation_config.json").read_text(encoding="utf-8"))

    validator = DataValidator(df)
    findings = validator.run_all(config)
    summary = DataValidator.summarize(findings)
    log.info("checks: %d passed, %d failed", summary["pass"], summary["fail"])

    out = EXAMPLE / "sample_report.md"
    write_report(
        str(out),
        findings,
        profile(df),
        title="Sample Orders — Data Quality Report",
        source="example/sample_data.csv (synthetic)",
    )
    log.info("report written to %s", out)
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
