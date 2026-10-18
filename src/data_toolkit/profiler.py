"""Quick, dependency-free dataset profiling for pandas DataFrames."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

_TOP_N_CATEGORICAL = 5


def profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Return a JSON-serializable profile of ``df``.

    Includes shape, dtypes, null counts/ratios, numeric ``describe()``
    statistics and top values for categorical columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"expected pandas DataFrame, got {type(df).__name__}")

    numeric = df.select_dtypes(include="number")
    categorical = df.select_dtypes(include=["object", "string", "category", "bool"])

    numeric_summary: Dict[str, Dict[str, float]] = {}
    if not numeric.empty:
        desc = numeric.describe(percentiles=[0.25, 0.5, 0.75])
        for col in desc.columns:
            numeric_summary[col] = {
                stat: float(desc.loc[stat, col]) for stat in desc.index
            }

    categorical_summary: Dict[str, Dict[str, int]] = {}
    for col in categorical.columns:
        top = df[col].value_counts(dropna=False).head(_TOP_N_CATEGORICAL)
        categorical_summary[col] = {
            (str(k) if pd.notna(k) else "<null>"): int(v) for k, v in top.items()
        }

    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": {col: int(n) for col, n in df.isna().sum().items()},
        "null_ratios": {col: float(r) for col, r in df.isna().mean().items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_summary": numeric_summary,
        "categorical_top_values": categorical_summary,
    }
