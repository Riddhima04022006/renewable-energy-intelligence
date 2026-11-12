
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_DIR / "india_monthly.csv"

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

df = pd.read_csv(
    INPUT_FILE,
    dtype=str,
    keep_default_na=False
)

# Convert dates and values without modifying the source.
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Numeric Value"] = pd.to_numeric(
    df["Value"].str.strip(),
    errors="coerce"
)

# --------------------------------------------------
# FILTER GENERATION IN GWh
# --------------------------------------------------

gen = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

gen["Month"] = gen["Date"].dt.to_period("M")

all_months = pd.period_range(
    gen["Month"].min(),
    gen["Month"].max(),
    freq="M"
)

all_variables = sorted(gen["Variable"].unique())
all_states = sorted(gen["State"].unique())

print("=" * 70)
print("GWh GENERATION PROFILE")
print("=" * 70)

print(f"Rows: {len(gen):,}")
print(f"States/labels: {len(all_states)}")
print(f"Variables: {len(all_variables)}")
print(f"Months: {len(all_months)}")

print("\nVARIABLES")
for variable in all_variables:
    print(" ", variable)

# --------------------------------------------------
# 1. STATE-VARIABLE COVERAGE
# --------------------------------------------------

profile = (
    gen.groupby(["State", "Variable"])
    .agg(
        rows=("Value", "size"),
        observed_months=("Month", "nunique"),
        numeric_values=("Numeric Value", "count"),
        blank_values=("Value", lambda s: s.str.strip().eq("").sum()),
        first_month=("Month", "min"),
        last_month=("Month", "max")
    )
    .reset_index()
)

profile["missing_months_within_full_range"] = (
    len(all_months) - profile["observed_months"]
)

profile["first_month"] = profile["first_month"].astype(str)
profile["last_month"] = profile["last_month"].astype(str)

profile.to_csv(
    OUTPUT_DIR / "02_state_variable_coverage.csv",
    index=False
)

print("\n" + "=" * 70)
print("STATE-VARIABLE COVERAGE")
print("=" * 70)

print(
    profile[
        (profile["blank_values"] > 0) |
        (profile["missing_months_within_full_range"] > 0)
    ].to_string(index=False)
)

# --------------------------------------------------
# 2. STATE-MONTH COMPLETENESS
# --------------------------------------------------

state_month = (
    gen.groupby(["State", "Month"])
    .agg(
        rows=("Variable", "size"),
        unique_variables=("Variable", "nunique"),
        numeric_values=("Numeric Value", "count")
    )
    .reset_index()
)

expected_variables = len(all_variables)

state_month["missing_variable_records"] = (
    expected_variables - state_month["unique_variables"]
)

state_month["blank_value_records"] = (
    state_month["rows"] - state_month["numeric_values"]
)

state_month["complete"] = (
    (state_month["unique_variables"] == expected_variables) &
    (state_month["numeric_values"] == expected_variables)
)

state_month["Month"] = state_month["Month"].astype(str)

state_month.to_csv(
    OUTPUT_DIR / "02_state_month_completeness.csv",
    index=False
)

print("\n" + "=" * 70)
print("STATE-MONTH COMPLETENESS")
print("=" * 70)

summary = (
    state_month.groupby("State")
    .agg(
        observed_state_months=("Month", "size"),
        complete_state_months=("complete", "sum"),
        incomplete_state_months=("complete", lambda s: (~s).sum()),
        minimum_variables=("unique_variables", "min"),
        maximum_variables=("unique_variables", "max"),
        total_blank_values=("blank_value_records", "sum")
    )
    .reset_index()
)

print(summary.to_string(index=False))

# --------------------------------------------------
# 3. DUPLICATE CHECK
# --------------------------------------------------

duplicate_mask = gen.duplicated(
    subset=["State", "Date", "Variable", "Unit"],
    keep=False
)

duplicates = gen[duplicate_mask].sort_values(
    ["State", "Date", "Variable"]
)

print("\n" + "=" * 70)
print("DUPLICATE CHECK")
print("=" * 70)

print(f"Duplicate rows: {len(duplicates):,}")

if not duplicates.empty:
    duplicates.to_csv(
        OUTPUT_DIR / "02_gwh_duplicates.csv",
        index=False
    )
    print("Duplicate records saved.")

# --------------------------------------------------
# 4. BLANK VALUE RECORDS
# --------------------------------------------------

blank_records = gen[
    gen["Value"].str.strip().eq("")
].copy()

print("\n" + "=" * 70)
print("BLANK GWh RECORDS")
print("=" * 70)

print(f"Blank GWh records: {len(blank_records):,}")

if not blank_records.empty:
    blank_summary = (
        blank_records.groupby(["State", "Variable"])
        .size()
        .reset_index(name="blank_records")
        .sort_values("blank_records", ascending=False)
    )

    print(blank_summary.to_string(index=False))

    blank_records.to_csv(
        OUTPUT_DIR / "02_blank_gwh_records.csv",
        index=False
    )

print("\nAll outputs saved in:", OUTPUT_DIR)
