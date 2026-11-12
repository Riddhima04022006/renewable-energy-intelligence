
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent / "outputs"
REPORT = BASE / "frontend_data_inventory.txt"

FILES = [
    "state_month_analysis.csv",
    "national_month_analysis.csv",
    "04_annual_national_summary.csv",
    "04_monthly_national_metrics.csv",
    "07_national_annual_source_summary.csv",
    "07_national_monthly_source_metrics.csv",
    "07_national_source_composition.csv",
    "07_annual_state_source_summary.csv",
    "07_state_source_period_metrics.csv",
    "07_state_source_rankings.csv",
    "09_national_capacity_summary.csv",
    "09_annual_state_capacity_summary.csv",
    "09_state_period_capacity_summary.csv",
    "10_national_source_capacity_factor_summary.csv",
    "10_state_source_capacity_factor_summary.csv",
    "12_capacity_factor_sensitivity.csv",
    "13_adjusted_state_capacity_factor_rankings.csv",
    "13_capacity_factor_exclusion_register.csv",
    "15_monthly_state_emissions.csv",
    "15_annual_state_emissions_summary.csv",
    "15_state_period_emissions_summary.csv",
    "15_state_emissions_2024_2025_comparison.csv",
]

lines = []


def out(text=""):
    lines.append(str(text))


def inspect_file(name):
    path = BASE / name
    out(f"\n{'=' * 65}\n{name}")

    if not path.exists():
        out("MISSING FILE")
        return

    df = pd.read_csv(path, low_memory=False)

    out(f"Shape: {df.shape}")
    out("Columns:")
    out(" | ".join(f"{c} [{df[c].dtype}]" for c in df.columns))

    missing = df.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        out("Missing: " + " | ".join(
            f"{k}={v}" for k, v in missing.items()
        ))

    # Date range
    for col in df.columns:
        if col.lower() in ("date", "month"):
            dates = pd.to_datetime(df[col], errors="coerce")
            if dates.notna().any():
                out(
                    f"{col} range: "
                    f"{dates.min().date()} to {dates.max().date()}"
                )

    # Important categorical columns
    for col in df.columns:
        if col.lower() in (
            "state", "source", "category", "variable",
            "metric", "unit", "period", "year"
        ):
            values = df[col].dropna().astype(str).unique()
            if len(values) <= 25:
                out(f"{col} values: {', '.join(values)}")
            else:
                out(f"{col} unique count: {len(values)}")

    # Only two representative rows
    out("Sample records:")
    out(df.head(2).to_string(index=False, max_cols=15))

    # Numeric range, not full descriptive statistics
    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        out("Numeric ranges:")
        for col in numeric.columns:
            out(
                f"  {col}: "
                f"{numeric[col].min()} to {numeric[col].max()}"
            )


out("FRONTEND DATA INVENTORY")
out(f"Output directory: {BASE}")

for filename in FILES:
    inspect_file(filename)

out("\n" + "=" * 65)
out("CHART FILES")

charts = BASE / "charts"
if charts.exists():
    for path in sorted(charts.rglob("*")):
        if path.is_file():
            out(f"{path.relative_to(BASE)} ({path.stat().st_size} bytes)")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"Report created: {REPORT}")
print(f"Report lines: {len(lines)}")
print(f"Report size: {REPORT.stat().st_size:,} bytes")
