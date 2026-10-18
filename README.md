# python-data-analysis-automation-toolkit

A Python toolkit that automates the boring parts of data analysis: **schema and
data-quality checks**, **dataset profiling**, and **Markdown reporting** — usable
as a library or from the command line.

Built by [Vishwaraj Algude](https://github.com/TONYISFIT) as a portfolio
project demonstrating pandas-based data automation, typed Python packaging,
pytest, and GitHub Actions CI.

## Features

- `DataValidator` — null checks, primary-key uniqueness, dtype checks, numeric
  range checks, and duplicate-row detection; returns structured findings
  (`check`, `column`, `status`, `details`)
- `profile(df)` — shape, dtypes, null counts/ratios, numeric `describe()`
  stats, top categorical values
- `render_markdown_report()` / `write_report()` — findings + profile as a
  clean Markdown report
- `data-toolkit` CLI with `validate`, `profile`, and `report` subcommands,
  logging (not `print`), and meaningful exit codes:
  `0` = all checks passed, `1` = validation failures found, `2` = usage/I-O error
- Full type hints, pytest suite, CI on Python 3.10 / 3.11 / 3.12

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

Requires Python ≥ 3.10. Dependencies: `pandas`, `openpyxl` (Excel support).

## Quick start — CLI

Validate the bundled synthetic sample (it intentionally contains nulls,
a duplicate key, an out-of-range value, and duplicated rows):

```bash
data-toolkit validate example/sample_data.csv --config example/validation_config.json
```

Real output:

```
INFO: [PASS] nulls on order_id: 0/12 nulls (0.0%), threshold 0.0%
INFO: [PASS] nulls on customer_name: 0/12 nulls (0.0%), threshold 0.0%
INFO: [PASS] nulls on amount: 0/12 nulls (0.0%), threshold 0.0%
WARNING: [FAIL] unique on order_id: 3 duplicate rows on key (order_id); e.g. [{'order_id': 1002}]
INFO: [PASS] dtypes on amount: expected float64, found float64
INFO: [PASS] dtypes on order_id: expected int64, found int64
INFO: [PASS] dtypes on quantity: expected int64, found int64
WARNING: [FAIL] ranges on amount: 1 out-of-range values (min=0, max=100000); observed {'min': -499.0, 'max': -499.0}
INFO: [PASS] ranges on quantity: all values within [1, 100]
WARNING: [FAIL] duplicates on *: 2 duplicate rows
INFO: validation complete: 7 passed, 3 failed
```

(exit code `1` — validation failures found)

Profile a dataset:

```bash
data-toolkit profile example/sample_data.csv
```

```
INFO: rows=12 columns=7 duplicates=2
INFO:   order_id             int64      nulls=0 (0.0%)
INFO:   customer_name        object     nulls=0 (0.0%)
INFO:   customer_email       object     nulls=2 (16.7%)
INFO:   product              object     nulls=0 (0.0%)
INFO:   quantity             int64      nulls=0 (0.0%)
INFO:   amount               float64    nulls=0 (0.0%)
INFO:   order_date           object     nulls=0 (0.0%)
```

Generate the full Markdown report:

```bash
data-toolkit report example/sample_data.csv \
    --config example/validation_config.json \
    --output qa_report.md \
    --title "Orders — Data Quality Report"
```

## Python API

```python
import json
import pandas as pd
from data_toolkit import DataValidator, profile, write_report

df = pd.read_csv("example/sample_data.csv", comment="#")
config = json.load(open("example/validation_config.json"))

validator = DataValidator(df)
findings = validator.run_all(config)          # list of Finding dicts
print(DataValidator.summarize(findings))      # {'pass': 7, 'fail': 3}

write_report("qa_report.md", findings, profile(df),
             title="Orders — Data Quality Report",
             source="example/sample_data.csv (synthetic)")
```

Or run the end-to-end demo:

```bash
python example/usage.py
```

## Validation config reference

`run_all()` / the CLI `--config` accept a JSON object (all keys optional):

```json
{
  "not_null": ["order_id", "customer_name"],
  "max_null_ratio": 0.0,
  "unique": ["order_id"],
  "dtypes": {"amount": "float64"},
  "ranges": {"amount": {"min": 0, "max": 100000}},
  "no_duplicates": true,
  "duplicate_subset": ["order_id", "product"]
}
```

## Project structure

```
src/data_toolkit/
    __init__.py      package exports (version 0.1.0)
    validators.py    DataValidator — nulls, uniqueness, dtypes, ranges, duplicates
    profiler.py      profile(df) -> dict
    reporters.py     Markdown report rendering
    cli.py           argparse CLI (validate / profile / report)
example/
    sample_data.csv          synthetic demo data (labelled synthetic in-file)
    validation_config.json   demo validation config
    usage.py                 end-to-end demo script
tests/
    test_validators.py       20 tests — pass/fail cases for every check
    test_profiler.py         11 tests — profile + report rendering
    test_cli.py               8 tests — subcommands, exit codes, logging
.github/workflows/ci.yml     pytest on Python 3.10, 3.11, 3.12
```

## Testing

```bash
pytest -q
```

39 tests, all passing. CI runs the same suite on every push via GitHub Actions.

## Notes

- `example/sample_data.csv` is **synthetic data generated for demonstration** —
  labelled as such inside the file. It deliberately contains quality issues so
  the demo shows real findings.
- CSV lines starting with `#` are treated as comments by the loader.
- Exit codes make the CLI safe to gate pipelines: fail a build when data
  validation fails.

## License

MIT — see [LICENSE](LICENSE). © 2026 Vishwaraj Algude.
