"""Tests for data_toolkit.profiler and data_toolkit.reporters."""

import pandas as pd
import pytest

from data_toolkit import profile, render_markdown_report, write_report
from data_toolkit.validators import DataValidator


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [1, 2, 3, 3],
            "amount": [10.0, 20.0, None, 40.0],
            "product": ["mouse", "keyboard", "mouse", "mouse"],
        }
    )


def test_profile_shape_and_dtypes(df: pd.DataFrame) -> None:
    prof = profile(df)
    assert prof["rows"] == 4
    assert prof["columns"] == 3
    assert prof["column_names"] == ["order_id", "amount", "product"]
    assert prof["dtypes"]["order_id"] == "int64"


def test_profile_nulls(df: pd.DataFrame) -> None:
    prof = profile(df)
    assert prof["null_counts"] == {"order_id": 0, "amount": 1, "product": 0}
    assert prof["null_ratios"]["amount"] == pytest.approx(0.25)


def test_profile_duplicates(df: pd.DataFrame) -> None:
    assert profile(df)["duplicate_rows"] == 0
    duped = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    assert profile(duped)["duplicate_rows"] == 1


def test_profile_numeric_summary(df: pd.DataFrame) -> None:
    numeric = profile(df)["numeric_summary"]
    assert numeric["amount"]["count"] == pytest.approx(3.0)
    assert numeric["amount"]["mean"] == pytest.approx(70.0 / 3)
    assert numeric["amount"]["min"] == pytest.approx(10.0)
    assert numeric["amount"]["max"] == pytest.approx(40.0)


def test_profile_categorical_top_values(df: pd.DataFrame) -> None:
    top = profile(df)["categorical_top_values"]["product"]
    assert top["mouse"] == 3
    assert top["keyboard"] == 1


def test_profile_rejects_non_dataframe() -> None:
    with pytest.raises(TypeError):
        profile([1, 2, 3])  # type: ignore[arg-type]


def test_profile_json_serializable(df: pd.DataFrame) -> None:
    import json

    json.dumps(profile(df))  # must not raise


def _sample_findings(df: pd.DataFrame):
    return DataValidator(df).run_all({"unique": ["order_id"], "not_null": ["amount"]})


def test_report_contains_findings_and_profile(df: pd.DataFrame) -> None:
    findings = _sample_findings(df)
    report = render_markdown_report(findings, profile(df), title="Test Report")
    assert "# Test Report" in report
    assert "## Validation findings" in report
    assert "## Dataset profile" in report
    assert "unique" in report
    assert "❌" in report  # order_id has duplicates -> at least one failure


def test_report_summary_counts(df: pd.DataFrame) -> None:
    findings = _sample_findings(df)
    report = render_markdown_report(findings, profile(df))
    n_fail = sum(1 for f in findings if f["status"] == "fail")
    assert f"Failed: **{n_fail}**" in report


def test_write_report(tmp_path, df: pd.DataFrame) -> None:
    out = tmp_path / "report.md"
    returned = write_report(str(out), _sample_findings(df), profile(df))
    assert returned == str(out)
    assert out.exists()
    assert "# Data Quality Report" in out.read_text(encoding="utf-8")
