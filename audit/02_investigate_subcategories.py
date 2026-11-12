
import pandas as pd

# Load the original dataset
df = pd.read_csv("../india_monthly.csv")

# Treat Value as numeric for this check.
# Values that cannot be converted to numbers become NaN.
df["Value_numeric"] = pd.to_numeric(df["Value"], errors="coerce")

# Summarise how each Category/Subcategory combination is structured
summary = (
    df.groupby(
        ["Category", "Subcategory", "Variable", "Unit"],
        dropna=False
    ).agg(
        rows=("Value", "size"),
        numeric_values=("Value_numeric", "count"),
        states=("State", "nunique"),
        months=("Date", "nunique")
    )
    .reset_index()
    .sort_values(["Category", "Subcategory", "Variable", "Unit"])
)

print(summary.to_string(index=False))
