"""Data-quality checks that return structured, machine-readable findings.

Every check returns a list of :class:`Finding` dicts with the keys
``check``, ``column``, ``status`` (``"pass"`` or ``"fail"``) and ``details``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TypedDict

import pandas as pd


class Finding(TypedDict):
    """One structured validation result."""

    check: str
    column: str
    status: str  # "pass" | "fail"
    details: str


def _finding(check: str, column: str, passed: bool, details: str) -> Finding:
    return {
        "check": check,
        "column": column,
        "status": "pass" if passed else "fail",
        "details": details,
    }


class DataValidator:
    """Run data-quality checks against a pandas DataFrame.

    Parameters
    ----------
    df:
        The DataFrame to validate. It is never mutated.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"expected pandas DataFrame, got {type(df).__name__}")
        self.df = df

    # ------------------------------------------------------------------ checks
    def check_nulls(
        self,
        columns: Optional[Sequence[str]] = None,
        max_null_ratio: float = 0.0,
    ) -> List[Finding]:
        """Fail columns whose null ratio exceeds ``max_null_ratio``."""
        cols = list(columns) if columns is not None else list(self.df.columns)
        findings: List[Finding] = []
        for col in cols:
            if col not in self.df.columns:
                findings.append(
                    _finding("nulls", col, False, f"column '{col}' not in DataFrame")
                )
                continue
            ratio = float(self.df[col].isna().mean())
            n_null = int(self.df[col].isna().sum())
            passed = ratio <= max_null_ratio
            findings.append(
                _finding(
                    "nulls",
                    col,
                    passed,
                    f"{n_null}/{len(self.df)} nulls ({ratio:.1%}), "
                    f"threshold {max_null_ratio:.1%}",
                )
            )
        return findings

    def check_unique(self, columns: Sequence[str]) -> List[Finding]:
        """Fail when a column (or column combo) that should be unique has duplicates.

        Use for primary-key / natural-key checks.
        """
        findings: List[Finding] = []
        cols = list(columns)
        missing = [c for c in cols if c not in self.df.columns]
        if missing:
            return [
                _finding("unique", ",".join(cols), False, f"missing columns: {missing}")
            ]
        dup_mask = self.df.duplicated(subset=cols, keep=False)
        n_dup = int(dup_mask.sum())
        if n_dup:
            dup_values = self.df.loc[dup_mask, cols].drop_duplicates().head(5)
            sample = dup_values.to_dict(orient="records")
            details = f"{n_dup} duplicate rows on key ({', '.join(cols)}); e.g. {sample}"
        else:
            details = f"all {len(self.df)} values unique on key ({', '.join(cols)})"
        findings.append(_finding("unique", ",".join(cols), n_dup == 0, details))
        return findings

    def check_dtypes(self, expected: Dict[str, str]) -> List[Finding]:
        """Fail when a column's dtype does not match the expected dtype.

        ``expected`` maps column name -> pandas dtype name, e.g. ``"int64"``.
        """
        findings: List[Finding] = []
        for col, want in expected.items():
            if col not in self.df.columns:
                findings.append(
                    _finding("dtypes", col, False, f"column '{col}' not in DataFrame")
                )
                continue
            actual = str(self.df[col].dtype)
            passed = actual == want
            findings.append(
                _finding("dtypes", col, passed, f"expected {want}, found {actual}")
            )
        return findings

    def check_ranges(
        self,
        ranges: Dict[str, Dict[str, Optional[float]]],
    ) -> List[Finding]:
        """Fail when numeric values fall outside ``{"min": x, "max": y}`` bounds.

        Either bound may be ``None`` (unbounded on that side). Non-numeric
        columns fail the check.
        """
        findings: List[Finding] = []
        for col, bounds in ranges.items():
            if col not in self.df.columns:
                findings.append(
                    _finding("ranges", col, False, f"column '{col}' not in DataFrame")
                )
                continue
            series = pd.to_numeric(self.df[col], errors="coerce")
            if series.isna().all() and self.df[col].notna().any():
                findings.append(
                    _finding("ranges", col, False, "column is not numeric")
                )
                continue
            lo = bounds.get("min")
            hi = bounds.get("max")
            bad = pd.Series(False, index=series.index)
            if lo is not None:
                bad |= series < lo
            if hi is not None:
                bad |= series > hi
            n_bad = int(bad.sum())
            worst = series[bad].agg(["min", "max"]).to_dict() if n_bad else {}
            details = (
                f"{n_bad} out-of-range values (min={lo}, max={hi}); observed {worst}"
                if n_bad
                else f"all values within [{lo}, {hi}]"
            )
            findings.append(_finding("ranges", col, n_bad == 0, details))
        return findings

    def check_duplicates(self, subset: Optional[Sequence[str]] = None) -> List[Finding]:
        """Fail when fully duplicated rows (or duplicates on ``subset``) exist."""
        dup_mask = self.df.duplicated(subset=list(subset) if subset else None, keep="first")
        n_dup = int(dup_mask.sum())
        label = f" on ({', '.join(subset)})" if subset else ""
        details = (
            f"{n_dup} duplicate rows{label}"
            if n_dup
            else f"no duplicate rows{label}"
        )
        return [_finding("duplicates", ",".join(subset) if subset else "*", n_dup == 0, details)]

    # -------------------------------------------------------------- orchestration
    def run_all(self, config: Dict[str, Any]) -> List[Finding]:
        """Run a config dict of checks and return all findings.

        Config keys (all optional)::

            {
                "not_null": ["order_id", "amount"],      # max_null_ratio applies
                "max_null_ratio": 0.0,
                "unique": ["order_id"],                  # primary-key check
                "dtypes": {"amount": "float64"},
                "ranges": {"amount": {"min": 0, "max": 100000}},
                "no_duplicates": true,
                "duplicate_subset": ["order_id", "product"],
            }
        """
        findings: List[Finding] = []
        if "not_null" in config or "max_null_ratio" in config:
            findings += self.check_nulls(
                config.get("not_null"), config.get("max_null_ratio", 0.0)
            )
        if "unique" in config:
            findings += self.check_unique(config["unique"])
        if "dtypes" in config:
            findings += self.check_dtypes(config["dtypes"])
        if "ranges" in config:
            findings += self.check_ranges(config["ranges"])
        if config.get("no_duplicates"):
            findings += self.check_duplicates(config.get("duplicate_subset"))
        return findings

    @staticmethod
    def summarize(findings: Sequence[Finding]) -> Dict[str, int]:
        """Count findings by status."""
        summary = {"pass": 0, "fail": 0}
        for f in findings:
            summary[f["status"]] = summary.get(f["status"], 0) + 1
        return summary
