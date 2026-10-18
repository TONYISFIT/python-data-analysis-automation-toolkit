"""Tests for the data-toolkit CLI (argparse subcommands, exit codes, logging)."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from data_toolkit.cli import EXIT_ERROR, EXIT_OK, EXIT_VALIDATION_FAILED, main

EXAMPLE = Path(__file__).resolve().parent.parent / "example"
SAMPLE_CSV = EXAMPLE / "sample_data.csv"
CONFIG = EXAMPLE / "validation_config.json"


@pytest.fixture
def clean_csv(tmp_path: Path) -> Path:
    p = tmp_path / "clean.csv"
    pd.DataFrame({"id": [1, 2, 3], "amount": [10.0, 20.0, 30.0]}).to_csv(p, index=False)
    return p


@pytest.fixture
def clean_config(tmp_path: Path) -> Path:
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps({"unique": ["id"], "not_null": ["id"], "ranges": {"amount": {"min": 0}}}),
        encoding="utf-8",
    )
    return p


def test_validate_pass_exit_code(clean_csv: Path, clean_config: Path) -> None:
    assert main(["validate", str(clean_csv), "--config", str(clean_config)]) == EXIT_OK


def test_validate_fail_exit_code() -> None:
    # sample_data.csv intentionally contains quality issues
    assert main(["validate", str(SAMPLE_CSV), "--config", str(CONFIG)]) == EXIT_VALIDATION_FAILED


def test_validate_missing_input_returns_error(clean_config: Path, tmp_path: Path) -> None:
    assert main(["validate", str(tmp_path / "nope.csv"), "--config", str(clean_config)]) == EXIT_ERROR


def test_validate_bad_config_returns_error(clean_csv: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    assert main(["validate", str(clean_csv), "--config", str(bad)]) == EXIT_ERROR


def test_validate_writes_report(clean_csv: Path, clean_config: Path, tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    rc = main(["validate", str(clean_csv), "--config", str(clean_config), "--output", str(out)])
    assert rc == EXIT_OK
    assert out.exists()
    assert "## Validation findings" in out.read_text(encoding="utf-8")


def test_profile_runs(clean_csv: Path) -> None:
    assert main(["profile", str(clean_csv)]) == EXIT_OK


def test_profile_json_output(clean_csv: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["profile", str(clean_csv), "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["rows"] == 3


def test_report_subcommand(clean_csv: Path, clean_config: Path, tmp_path: Path) -> None:
    out = tmp_path / "full.md"
    rc = main(
        ["report", str(clean_csv), "--config", str(clean_config),
         "--output", str(out), "--title", "My Report"]
    )
    assert rc == EXIT_OK
    assert "# My Report" in out.read_text(encoding="utf-8")


def test_report_subcommand_fails_on_dirty_data(tmp_path: Path) -> None:
    out = tmp_path / "dirty.md"
    rc = main(["report", str(SAMPLE_CSV), "--config", str(CONFIG), "--output", str(out)])
    assert rc == EXIT_VALIDATION_FAILED
    assert out.exists()  # report is still written


def test_cli_entrypoint_via_subprocess(clean_csv: Path, clean_config: Path) -> None:
    """The console_script entry point path (python -m) works end to end."""
    env = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "data_toolkit.cli", "validate", str(clean_csv),
         "--config", str(clean_config)],
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), **env},
    )
    assert proc.returncode == EXIT_OK, proc.stderr
