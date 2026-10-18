"""data_toolkit — automate data validation and reporting.

A small, dependency-light toolkit for analysts:

- :class:`~data_toolkit.validators.DataValidator` — schema and data-quality checks
- :func:`~data_toolkit.profiler.profile` — quick dataset profiling
- :func:`~data_toolkit.reporters.render_markdown_report` — Markdown reports

Example:
    >>> from data_toolkit import DataValidator, profile, render_markdown_report
    >>> import pandas as pd
    >>> df = pd.read_csv("orders.csv")
    >>> validator = DataValidator(df)
    >>> findings = validator.run_all({"unique": ["order_id"], "not_null": ["order_id"]})
    >>> report = render_markdown_report(findings, profile(df), title="Orders QA")
"""

__version__ = "0.1.0"
__author__ = "Vishwaraj Algude"

from data_toolkit.profiler import profile
from data_toolkit.reporters import render_markdown_report, write_report
from data_toolkit.validators import DataValidator, Finding

__all__ = [
    "DataValidator",
    "Finding",
    "profile",
    "render_markdown_report",
    "write_report",
    "__version__",
]
