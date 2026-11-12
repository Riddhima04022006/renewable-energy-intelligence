
import pandas as pd

df = pd.read_csv(
    "../india_monthly.csv",
    dtype=str,
    keep_default_na=False
)

# Identify blank Value fields
df["Value"] = df["Value"].str.strip()
missing = df[df["Value"] == ""].copy()

# Convert Date into datetime for time-based analysis
missing["Date"] = pd.to_datetime(
    missing["Date"],
    errors="coerce"
)

missing["Year"] = missing["Date"].dt.year
missing["Month"] = missing["Date"].dt.to_period("M")

print("TOTAL BLANK VALUES:", len(missing))


# 1. VARIABLE-WISE DISTRIBUTION
print("\n--- 1. BLANK VALUES BY MEASUREMENT SERIES ---")

variable_summary = (
    missing.groupby(
        ["Category", "Subcategory", "Variable", "Unit"]
    )
    .agg(
        blank_records=("Value", "size"),
        affected_states=("State", "nunique"),
        first_missing_month=("Month", "min"),
        last_missing_month=("Month", "max")
    )
    .reset_index()
    .sort_values("blank_records", ascending=False)
)

print(variable_summary.to_string(index=False))


# 2. STATE-WISE DISTRIBUTION
print("\n--- 2. BLANK VALUES BY STATE ---")

state_summary = (
    missing.groupby("State")
    .agg(
        blank_records=("Value", "size"),
        affected_series=("Variable", "nunique"),
        first_missing_month=("Month", "min"),
        last_missing_month=("Month", "max")
    )
    .reset_index()
    .sort_values("blank_records", ascending=False)
)

print(state_summary.to_string(index=False))


# 3. YEAR-WISE DISTRIBUTION
print("\n--- 3. BLANK VALUES BY YEAR ---")

print(
    missing.groupby("Year")
    .size()
    .sort_index()
    .to_string()
)


# 4. CATEGORY-WISE DISTRIBUTION
print("\n--- 4. BLANK VALUES BY CATEGORY ---")

print(
    missing.groupby("Category")
    .size()
    .sort_values(ascending=False)
    .to_string()
)


# 5. MOST AFFECTED STATE-VARIABLE COMBINATIONS
print("\n--- 5. STATE-VARIABLE COMBINATIONS ---")

state_variable_summary = (
    missing.groupby(
        ["State", "Category", "Variable", "Unit"]
    )
    .size()
    .reset_index(name="blank_records")
    .sort_values("blank_records", ascending=False)
)

print(state_variable_summary.head(30).to_string(index=False))
