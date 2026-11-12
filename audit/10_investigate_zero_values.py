
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

numeric = df[df["Value"].notna()].copy()
zeros = numeric[numeric["Value"] == 0]

print("--- OVERALL ZERO VS MISSING ---")
print("Total records:", len(df))
print("Numeric records:", len(numeric))
print("Zero values:", len(zeros))
print("Non-zero numeric values:", len(numeric) - len(zeros))
print("Missing values:", df["Value"].isna().sum())

print("\n--- ZERO VALUES BY CATEGORY ---")
print(
    numeric.groupby("Category")
    .agg(
        numeric_records=("Value", "size"),
        zero_records=("Value", lambda x: (x == 0).sum())
    )
    .to_string()
)

print("\n--- ZERO VALUES BY MEASUREMENT SERIES ---")

summary = (
    numeric.groupby(
        ["Category", "Subcategory", "Variable", "Unit"]
    )
    .agg(
        numeric_records=("Value", "size"),
        zero_records=("Value", lambda x: (x == 0).sum())
    )
    .reset_index()
)

summary["zero_percentage"] = (
    summary["zero_records"] / summary["numeric_records"] * 100
).round(2)

print(
    summary.sort_values(
        "zero_records", ascending=False
    ).head(25).to_string(index=False)
)
