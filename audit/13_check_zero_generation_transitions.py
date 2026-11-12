
import pandas as pd

# Load the dataset
df = pd.read_csv("../india_monthly.csv")

# Convert Value to numeric
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

# Keep individual fuel generation in GWh
fuels = [
    "Solar", "Wind", "Hydro", "Bioenergy",
    "Coal", "Gas", "Nuclear", "Other Fossil",
    "Other Renewables"
]

df = df[
    (df["Category"] == "Electricity generation") &
    (df["Subcategory"] == "Fuel") &
    (df["Unit"] == "GWh") &
    (df["Variable"].isin(fuels))
].copy()

# Exclude non-geographic aggregate labels from state-level analysis
df = df[~df["State"].isin(["India Total", "Others"])]

# Convert dates to monthly periods
df["Month"] = pd.to_datetime(df["Date"]).dt.to_period("M")

# Sort observations chronologically
df = df.sort_values(["State", "Variable", "Month"])

results = []

for (state, fuel), group in df.groupby(["State", "Variable"]):

    group = group.sort_values("Month").copy()

    # Retain numeric observations only for transition checks
    valid = group[group["Value"].notna()].copy()

    if valid.empty:
        continue

    previous_value = valid["Value"].shift(1)

    # Convert monthly periods into consecutive integer indices
    month_index = valid["Month"].astype("int64")

    # A transition is valid only between consecutive months
    consecutive = month_index.diff().eq(1)

    zero_to_positive = (
        consecutive &
        (previous_value == 0) &
        (valid["Value"] > 0)
    )

    positive_to_zero = (
        consecutive &
        (previous_value > 0) &
        (valid["Value"] == 0)
    )

    positive_months = valid.loc[valid["Value"] > 0, "Month"]

    results.append({
        "State": state,
        "Fuel": fuel,
        "Numeric months": len(valid),
        "Zero to positive": int(zero_to_positive.sum()),
        "Positive to zero": int(positive_to_zero.sum()),
        "First recorded positive month": (
            str(positive_months.min())
            if not positive_months.empty else None
        )
    })

result = pd.DataFrame(results)

print("=== ZERO-GENERATION TRANSITION SUMMARY ===")

summary = result.groupby("Fuel").agg(
    State_series=("State", "count"),
    Series_with_positive_generation=(
        "First recorded positive month",
        lambda x: x.notna().sum()
    ),
    Zero_to_positive=("Zero to positive", "sum"),
    Positive_to_zero=("Positive to zero", "sum")
)

print(summary.to_string())

print("\n=== FIRST RECORDED POSITIVE MONTHS ===")

first_positive = (
    result.dropna(subset=["First recorded positive month"])
    ["First recorded positive month"]
    .value_counts()
    .sort_index()
)

print(first_positive.to_string())
