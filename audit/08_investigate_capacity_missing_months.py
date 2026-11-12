
import pandas as pd

df = pd.read_csv(
    "../india_monthly.csv",
    dtype=str,
    keep_default_na=False
)

df["Value"] = df["Value"].str.strip()
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.to_period("M")

# Focus only on Capacity records with blank values
missing_capacity = df[
    (df["Category"] == "Capacity") &
    (df["Value"] == "")
].copy()

# 1. Other Renewables: month-wise distribution
other_renewables = missing_capacity[
    (missing_capacity["Subcategory"] == "Fuel") &
    (missing_capacity["Variable"] == "Other Renewables") &
    (missing_capacity["Unit"] == "MW")
]

print("--- OTHER RENEWABLES: BLANKS BY MONTH ---")
print(
    other_renewables.groupby("Month")
    .size()
    .to_string()
)

print("\n--- OTHER RENEWABLES: BLANKS BY STATE ---")
print(
    other_renewables.groupby("State")
    .size()
    .sort_values(ascending=False)
    .to_string()
)


# 2. All other Capacity variables: month-wise distribution
other_capacity = missing_capacity[
    ~(
        (missing_capacity["Subcategory"] == "Fuel") &
        (missing_capacity["Variable"] == "Other Renewables") &
        (missing_capacity["Unit"] == "MW")
    )
]

print("\n--- OTHER CAPACITY VARIABLES: BLANKS BY VARIABLE ---")
print(
    other_capacity.groupby(
        ["Subcategory", "Variable", "Unit"]
    ).size().to_string()
)

print("\n--- OTHER CAPACITY VARIABLES: BLANKS BY MONTH ---")
print(
    other_capacity.groupby(
        ["Variable", "Month"]
    ).size().to_string()
)
