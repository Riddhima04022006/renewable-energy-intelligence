
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Date"] = pd.to_datetime(df["Date"])
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

# Individual fuel capacity
capacity = df[
    (df["Category"] == "Capacity") &
    (df["Subcategory"] == "Fuel") &
    (df["Unit"] == "MW")
][
    ["State", "Date", "Variable", "Value"]
].rename(columns={"Value": "Capacity_MW"})

# Individual fuel generation
generation = df[
    (df["Category"] == "Electricity generation") &
    (df["Subcategory"] == "Fuel") &
    (df["Unit"] == "GWh")
][
    ["State", "Date", "Variable", "Value"]
].rename(columns={"Value": "Generation_GWh"})

# Match capacity and generation
data = capacity.merge(
    generation,
    on=["State", "Date", "Variable"],
    how="inner",
    validate="one_to_one"
)

# Monthly hours
data["Hours_in_month"] = (
    data["Date"].dt.days_in_month * 24
)

# Identify invalid or unavailable measurements
zero_capacity = (
    data["Capacity_MW"].eq(0) &
    data["Generation_GWh"].gt(0)
)

negative_values = (
    data["Capacity_MW"].lt(0) |
    data["Generation_GWh"].lt(0)
)

valid = (
    data["Capacity_MW"].notna() &
    data["Generation_GWh"].notna() &
    data["Capacity_MW"].gt(0) &
    data["Generation_GWh"].ge(0)
)

# Calculate capacity factor only for valid records
data["Capacity_Factor_pct"] = pd.NA

data.loc[valid, "Capacity_Factor_pct"] = (
    data.loc[valid, "Generation_GWh"] * 1000 /
    (
        data.loc[valid, "Capacity_MW"] *
        data.loc[valid, "Hours_in_month"]
    ) * 100
)

# Summary by individual fuel
summary = (
    data[valid]
    .groupby("Variable")
    .agg(
        comparable=("Capacity_Factor_pct", "count"),
        median=("Capacity_Factor_pct", "median"),
        p95=("Capacity_Factor_pct",
             lambda x: x.quantile(0.95)),
        maximum=("Capacity_Factor_pct", "max"),
        above_100=("Capacity_Factor_pct",
                   lambda x: (x > 100).sum())
    )
    .reset_index()
)

print("=== D7.1: MONTHLY CAPACITY FACTOR ===")

print("\nMatched records:", len(data))
print("Valid capacity factor records:", valid.sum())
print("Zero capacity with positive generation:", zero_capacity.sum())
print("Negative capacity/generation records:", negative_values.sum())
print("Unavailable capacity or generation:",
      (~data["Capacity_MW"].notna() |
       ~data["Generation_GWh"].notna()).sum())

print("\n=== RESULTS BY FUEL ===")
print(summary.round(4).to_string(index=False))

print("\nTotal capacity factors above 100%:",
      (data.loc[valid, "Capacity_Factor_pct"] > 100).sum())
