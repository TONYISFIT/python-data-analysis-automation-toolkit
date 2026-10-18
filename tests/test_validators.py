"""Tests for data_toolkit.validators — pass and fail cases for every check."""

import pandas as pd
import pytest

from data_toolkit.validators import DataValidator


@pytest.fixture
def clean_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [1, 2, 3, 4],
            "customer": ["a", "b", "c", "d"],
            "amount": [10.0, 20.5, 30.0, 40.0],
            "qty": [1, 2, 1, 3],
        }
    )


@pytest.fixture
def dirty_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [1, 2, 2, 4],                      # duplicate key
            "customer": ["a", "b", None, "d"],            # one null
            "amount": [10.0, -5.0, 30.0, 40.0],           # one out of range
            "qty": [1, 2, 1, 3],
        }
    )


def test_rejects_non_dataframe() -> None:
    with pytest.raises(TypeError):
        DataValidator("not a dataframe")  # type: ignore[arg-type]


def test_check_nulls_pass(clean_df: pd.DataFrame) -> None:
    findings = DataValidator(clean_df).check_nulls(["order_id", "amount"])
    assert all(f["status"] == "pass" for f in findings)
    assert findings[0]["check"] == "nulls"


def test_check_nulls_fail(dirty_df: pd.DataFrame) -> None:
    findings = {f["column"]: f for f in DataValidator(dirty_df).check_nulls()}
    assert findings["customer"]["status"] == "fail"
    assert "1/4" in findings["customer"]["details"]
    assert findings["order_id"]["status"] == "pass"


def test_check_nulls_missing_column(clean_df: pd.DataFrame) -> None:
    findings = DataValidator(clean_df).check_nulls(["nope"])
    assert findings[0]["status"] == "fail"
    assert "not in DataFrame" in findings[0]["details"]


def test_check_nulls_ratio_threshold(clean_df: pd.DataFrame) -> None:
    df = clean_df.copy()
    df.loc[0, "customer"] = None  # 25% nulls
    findings = DataValidator(df).check_nulls(["customer"], max_null_ratio=0.5)
    assert findings[0]["status"] == "pass"
    findings = DataValidator(df).check_nulls(["customer"], max_null_ratio=0.1)
    assert findings[0]["status"] == "fail"


def test_check_unique_pass(clean_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(clean_df).check_unique(["order_id"])
    assert finding["status"] == "pass"


def test_check_unique_fail(dirty_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(dirty_df).check_unique(["order_id"])
    assert finding["status"] == "fail"
    assert "duplicate" in finding["details"]


def test_check_dtypes_pass(clean_df: pd.DataFrame) -> None:
    findings = DataValidator(clean_df).check_dtypes({"order_id": "int64", "amount": "float64"})
    assert all(f["status"] == "pass" for f in findings)


def test_check_dtypes_fail(clean_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(clean_df).check_dtypes({"amount": "int64"})
    assert finding["status"] == "fail"
    assert "float64" in finding["details"]


def test_check_ranges_pass(clean_df: pd.DataFrame) -> None:
    findings = DataValidator(clean_df).check_ranges({"amount": {"min": 0, "max": 100}})
    assert all(f["status"] == "pass" for f in findings)


def test_check_ranges_fail(dirty_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(dirty_df).check_ranges({"amount": {"min": 0, "max": 100}})
    assert finding["status"] == "fail"
    assert "1 out-of-range" in finding["details"]


def test_check_ranges_open_ended(clean_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(clean_df).check_ranges({"amount": {"min": 0, "max": None}})
    assert finding["status"] == "pass"


def test_check_ranges_non_numeric(clean_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(clean_df).check_ranges({"customer": {"min": 0}})
    assert finding["status"] == "fail"
    assert "not numeric" in finding["details"]


def test_check_duplicates_pass(clean_df: pd.DataFrame) -> None:
    (finding,) = DataValidator(clean_df).check_duplicates()
    assert finding["status"] == "pass"


def test_check_duplicates_fail() -> None:
    df = pd.DataFrame({"a": [1, 1], "b": ["x", "x"]})
    (finding,) = DataValidator(df).check_duplicates()
    assert finding["status"] == "fail"
    assert "1 duplicate" in finding["details"]


def test_run_all_orchestration(dirty_df: pd.DataFrame) -> None:
    config = {
        "not_null": ["order_id", "customer"],
        "unique": ["order_id"],
        "dtypes": {"amount": "float64"},
        "ranges": {"amount": {"min": 0}},
        "no_duplicates": True,
    }
    findings = DataValidator(dirty_df).run_all(config)
    statuses = {(f["check"], f["column"]): f["status"] for f in findings}
    assert statuses[("nulls", "customer")] == "fail"
    assert statuses[("nulls", "order_id")] == "pass"
    assert statuses[("unique", "order_id")] == "fail"
    assert statuses[("dtypes", "amount")] == "pass"
    assert statuses[("ranges", "amount")] == "fail"
    assert statuses[("duplicates", "*")] == "pass"  # no fully-duplicated rows here


def test_run_all_empty_config(clean_df: pd.DataFrame) -> None:
    assert DataValidator(clean_df).run_all({}) == []


def test_summarize() -> None:
    findings = [
        {"check": "nulls", "column": "a", "status": "pass", "details": ""},
        {"check": "nulls", "column": "b", "status": "fail", "details": ""},
        {"check": "unique", "column": "a", "status": "fail", "details": ""},
    ]
    assert DataValidator.summarize(findings) == {"pass": 1, "fail": 2}


def test_does_not_mutate_input(clean_df: pd.DataFrame) -> None:
    before = clean_df.copy(deep=True)
    v = DataValidator(clean_df)
    v.run_all({"unique": ["order_id"], "no_duplicates": True})
    pd.testing.assert_frame_equal(clean_df, before)
