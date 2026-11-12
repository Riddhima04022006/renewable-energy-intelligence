
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

# Convert Date into a proper datetime format
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Find the first and last observed month for each state
coverage = (
    df.groupby("State")
    .agg(
        first_month=("Date", "min"),
        last_month=("Date", "max"),
        observed_months=("Date", "nunique")
    )
    .reset_index()
)

# Count the number of months between the first and last month, inclusive
coverage["expected_months"] = (
    (coverage["last_month"].dt.year - coverage["first_month"].dt.year) * 12
    + coverage["last_month"].dt.month
    - coverage["first_month"].dt.month
    + 1
)

# Calculate missing months within each state's observed span
coverage["missing_months"] = (
    coverage["expected_months"] - coverage["observed_months"]
)

# Show states with the most missing months first
coverage = coverage.sort_values(
    ["missing_months", "State"],
    ascending=[False, True]
)

print(coverage.to_string(index=False))
