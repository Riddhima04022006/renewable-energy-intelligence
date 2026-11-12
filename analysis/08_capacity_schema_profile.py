
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "india_monthly.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("A4: CAPACITY DATA SCHEMA PROFILE")
print("=" * 70)

df = pd.read_csv(INPUT_FILE, low_memory=False)

capacity = df[
    (df["Category"] == "Capacity") &
    (df["Unit"] == "MW")
].copy()

capacity["Date"] = pd.to_datetime(capacity["Date"], errors="coerce")
capacity["Value"] = pd.to_numeric(capacity["Value"], errors="coerce")
capacity["Month"] = capacity["Date"].dt.to_period("M").astype(str)

print("\nOVERALL PROFILE")
print("-" * 70)
print("Rows:", len(capacity))
print("States / labels:", capacity["State"].nunique())
print("Date range:", capacity["Month"].min(), "to", capacity["Month"].max())
print("Missing values:", capacity["Value"].isna().sum())
print("Zero values:", (capacity["Value"] == 0).sum())
print("Negative values:", (capacity["Value"] < 0).sum())

print("\nSUBCATEGORY AND UNIT PROFILE")
print("-" * 70)

subcategory_profile = (
    capacity.groupby(["Subcategory", "Unit"], dropna=False)
    .agg(
        Rows=("Value", "size"),
        Numeric_Values=("Value", "count"),
        States=("State", "nunique"),
        Variables=("Variable", "nunique")
    )
    .reset_index()
)

print(subcategory_profile.to_string(index=False))

print("\nVARIABLE PROFILE")
print("-" * 70)

variable_profile = (
    capacity.groupby("Variable", dropna=False)
    .agg(
        Rows=("Value", "size"),
        Numeric_Values=("Value", "count"),
        Missing_Values=("Value", lambda x: x.isna().sum()),
        Zero_Values=("Value", lambda x: (x == 0).sum()),
        Negative_Values=("Value", lambda x: (x < 0).sum()),
        States=("State", "nunique"),
        Months=("Month", "nunique"),
        First_Month=("Month", "min"),
        Last_Month=("Month", "max")
    )
    .reset_index()
    .sort_values("Variable")
)

print(variable_profile.to_string(index=False))

print("\nSTATE COVERAGE: JULY 2021 TO NOVEMBER 2025")
print("-" * 70)

state_period = capacity[
    (capacity["Month"] >= "2021-07") &
    (capacity["Month"] <= "2025-11")
].copy()

state_coverage = (
    state_period.groupby(["State", "Variable"])
    .agg(
        Observed_Months=("Month", "nunique"),
        Numeric_Values=("Value", "count"),
        Missing_Values=("Value", lambda x: x.isna().sum()),
        First_Month=("Month", "min"),
        Last_Month=("Month", "max")
    )
    .reset_index()
)

print(state_coverage.to_string(index=False))

print("\nDUPLICATE CHECK")
print("-" * 70)

key = ["State", "Date", "Subcategory", "Variable", "Unit"]

duplicates = capacity[capacity.duplicated(key, keep=False)]

print("Duplicate records:", len(duplicates))

if len(duplicates) > 0:
    print(duplicates[key + ["Value"]].head(20).to_string(index=False))

variable_profile.to_csv(
    OUTPUT_DIR / "08_capacity_variable_profile.csv",
    index=False
)

state_coverage.to_csv(
    OUTPUT_DIR / "08_capacity_state_coverage.csv",
    index=False
)

subcategory_profile.to_csv(
    OUTPUT_DIR / "08_capacity_subcategory_profile.csv",
    index=False
)

print("\nSaved:")
print("08_capacity_variable_profile.csv")
print("08_capacity_state_coverage.csv")
print("08_capacity_subcategory_profile.csv")

print("\nCAPACITY SCHEMA PROFILE COMPLETED")
