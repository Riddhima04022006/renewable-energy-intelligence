
import pandas as pd

df = pd.read_csv("../india_monthly.csv")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
]

result = (
    df.groupby(["Variable", "State"])
    .agg(
        records=("Value", "count"),
        zeros=("Value", lambda x: (x == 0).sum())
    )
    .reset_index()
)

result["zero_pct"] = (
    result["zeros"] / result["records"] * 100
).round(1)

print(result.sort_values(
    ["Variable", "zero_pct"],
    ascending=[True, False]
).to_string(index=False))
