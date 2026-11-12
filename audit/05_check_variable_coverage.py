
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

# Parse dates
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Define what makes a measurement series distinct
series_columns = [
    "State",
    "Category",
    "Subcategory",
    "Variable",
    "Unit"
]

# Summarise the time coverage of each series
coverage = (
    df.groupby(series_columns, dropna=False)
    .agg(
        first_month=("Date", "min"),
        last_month=("Date", "max"),
        observed_months=("Date", "nunique"),
        numeric_values=("Value", lambda x: pd.to_numeric(
            x, errors="coerce"
        ).notna().sum())
    )
    .reset_index()
)

# Count expected calendar months within each series' observed span
coverage["expected_months"] = (
    (coverage["last_month"].dt.year - coverage["first_month"].dt.year) * 12
    + coverage["last_month"].dt.month
    - coverage["first_month"].dt.month
    + 1
)

# Identify missing months within the observed span
coverage["missing_months"] = (
    coverage["expected_months"] - coverage["observed_months"]
)

# Show series with the most gaps first
coverage = coverage.sort_values(
    ["missing_months", "State", "Category", "Variable"],
    ascending=[False, True, True, True]
)

print("Total measurement series:", len(coverage))
print("\n--- SERIES WITH MISSING MONTHS WITHIN THEIR SPAN ---")

gaps = coverage[coverage["missing_months"] > 0]
print(gaps.to_string(index=False))

print("\n--- SERIES WITH THE FEWEST NUMERIC VALUES ---")
print(
    coverage.sort_values(
        ["numeric_values", "State", "Category", "Variable"]
    ).head(20).to_string(index=False)
)
