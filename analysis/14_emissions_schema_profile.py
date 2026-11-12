
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
BASE_DIR = Path(r"D:\Renewable energy intelligence platform")
INPUT_FILE = BASE_DIR / "india_monthly.csv"
OUTPUT_DIR = BASE_DIR / "analysis" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = OUTPUT_DIR / "14_emissions_schema_report.txt"
PROFILE_FILE = OUTPUT_DIR / "14_emissions_variable_profile.csv"
COVERAGE_FILE = OUTPUT_DIR / "14_emissions_state_coverage.csv"

# ------------------------------------------------------------
# LOAD AND FILTER
# ------------------------------------------------------------
df = pd.read_csv(INPUT_FILE)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

em = df[df["Category"] == "Power sector emissions"].copy()

if em.empty:
    raise ValueError(
        "No records found for Category = 'Power sector emissions'. "
        "Check the source category labels."
    )

em["Month"] = em["Date"].dt.to_period("M")

# State/UT records only; exclude national and Others from this panel.
state_em = em[
    ~em["State"].isin(["India Total", "Others"])
].copy()

# ------------------------------------------------------------
# VARIABLE PROFILE
# ------------------------------------------------------------
profile = (
    em.groupby(["Subcategory", "Variable", "Unit"], dropna=False)
    .agg(
        Total_Records=("Value", "size"),
        Numeric_Values=("Value", "count"),
        Missing_Values=("Value", lambda x: x.isna().sum()),
        Zero_Values=("Value", lambda x: (x == 0).sum()),
        Negative_Values=("Value", lambda x: (x < 0).sum()),
        State_Labels=("State", "nunique"),
        Months=("Month", "nunique"),
        First_Month=("Month", "min"),
        Last_Month=("Month", "max"),
    )
    .reset_index()
)

profile.to_csv(PROFILE_FILE, index=False)

# ------------------------------------------------------------
# STATE / UT COVERAGE
# ------------------------------------------------------------
coverage = (
    state_em.groupby(
        ["State", "Subcategory", "Variable", "Unit"],
        dropna=False
    )
    .agg(
        Records=("Value", "size"),
        Numeric_Values=("Value", "count"),
        Missing_Values=("Value", lambda x: x.isna().sum()),
        Zero_Values=("Value", lambda x: (x == 0).sum()),
        Unique_Months=("Month", "nunique"),
        First_Month=("Month", "min"),
        Last_Month=("Month", "max"),
    )
    .reset_index()
)

coverage.to_csv(COVERAGE_FILE, index=False)

# ------------------------------------------------------------
# VALIDATION SUMMARY
# ------------------------------------------------------------
report = []

report.append("=" * 70)
report.append("A4.3: EMISSIONS SCHEMA AND COVERAGE PROFILE")
report.append("=" * 70)

report.append("\nOVERALL PROFILE")
report.append("-" * 70)
report.append(f"Total emissions records: {len(em):,}")
report.append(f"State/UT records: {len(state_em):,}")
report.append(f"State labels including India Total and Others: {em['State'].nunique()}")
report.append(f"State/UT labels: {state_em['State'].nunique()}")
report.append(f"Unique months: {em['Month'].nunique()}")
report.append(
    f"Overall period: {em['Month'].min()} to {em['Month'].max()}"
)
report.append(f"Numeric values: {em['Value'].notna().sum():,}")
report.append(f"Missing values: {em['Value'].isna().sum():,}")
report.append(f"Zero values: {(em['Value'] == 0).sum():,}")
report.append(f"Negative values: {(em['Value'] < 0).sum():,}")

report.append("\nSUBCATEGORY COUNTS")
report.append("-" * 70)
report.append(
    em.groupby("Subcategory").size().to_string()
)

report.append("\nVARIABLE AND UNIT PROFILE")
report.append("-" * 70)
report.append(profile.to_string(index=False))

report.append("\nSTATE/UT COVERAGE — JULY 2021 TO NOVEMBER 2025")
report.append("-" * 70)

common_period = state_em[
    (state_em["Month"] >= pd.Period("2021-07", freq="M")) &
    (state_em["Month"] <= pd.Period("2025-11", freq="M"))
]

coverage_common = (
    common_period.groupby(["Subcategory", "Variable", "Unit"])
    .agg(
        State_Labels=("State", "nunique"),
        Records=("Value", "size"),
        Numeric_Values=("Value", "count"),
        Missing_Values=("Value", lambda x: x.isna().sum()),
        Unique_Months=("Month", "nunique"),
    )
    .reset_index()
)

report.append(coverage_common.to_string(index=False))

report.append("\nOUTPUT FILES")
report.append("-" * 70)
report.append(str(PROFILE_FILE))
report.append(str(COVERAGE_FILE))

REPORT_FILE.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print("\nSchema profile saved successfully.")
