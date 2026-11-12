
import pandas as pd

df = pd.read_csv(
    "../india_monthly.csv",
    dtype=str,
    keep_default_na=False
)

df["Value"] = df["Value"].str.strip()
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.to_period("M")

# Focus on capacity records missing from June to November 2025
missing = df[
    (df["Category"] == "Capacity") &
    (df["Value"] == "") &
    (df["Month"] >= pd.Period("2025-06")) &
    (df["Month"] <= pd.Period("2025-11"))
].copy()

print("--- MISSING CAPACITY RECORDS: JUNE–NOVEMBER 2025 ---")

# Identify affected states
print("\nAffected states:")
print(
    missing.groupby("State")
    .size()
    .sort_values(ascending=False)
    .to_string()
)

# Identify exactly which variables are missing for each state
print("\nState-wise missing variables:")
for state, group in missing.groupby("State"):
    print(f"\n{state}:")
    print(
        group.groupby("Variable")
        .size()
        .sort_values(ascending=False)
        .to_string()
    )

# Check whether the same states are missing every month
print("\n--- STATE-MONTH MISSING RECORD COUNTS ---")
print(
    missing.groupby(["State", "Month"])
    .size()
    .to_string()
)
