
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Date"] = pd.to_datetime(df["Date"])
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

# Keep only the absolute measurements needed for D7
capacity = df[
    (df["Category"] == "Capacity") &
    (df["Unit"] == "MW") &
    (df["Subcategory"].isin(["Fuel", "Aggregate fuel"]))
].copy()

generation = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh") &
    (df["Subcategory"].isin(["Fuel", "Aggregate fuel"]))
].copy()

emissions = df[
    (df["Category"] == "Power sector emissions") &
    (df["Unit"] == "ktCO2") &
    (df["Subcategory"].isin(["Fuel", "Aggregate fuel"]))
].copy()

# Print numeric coverage for each measurement series
print("=== D7: CROSS-CATEGORY SERIES INVENTORY ===")

for name, data in [
    ("Capacity", capacity),
    ("Generation", generation),
    ("Emissions", emissions)
]:
    summary = (
        data.groupby(["Subcategory", "Variable", "Unit"])
        .agg(
            rows=("Value", "size"),
            numeric=("Value", "count"),
            state_months=("Date", "nunique")
        )
        .reset_index()
    )

    print(f"\n=== {name.upper()} ===")
    print(summary.to_string(index=False))


# Compare availability using State, Date, Subcategory and Variable
keys = ["State", "Date", "Subcategory", "Variable"]

def compare_coverage(left, right, left_name, right_name):
    left_keys = left.loc[left["Value"].notna(), keys].drop_duplicates()
    right_keys = right.loc[right["Value"].notna(), keys].drop_duplicates()

    matched = left_keys.merge(
        right_keys,
        on=keys,
        how="inner",
        validate="one_to_one"
    )

    print(f"\n=== {left_name} vs {right_name} ===")
    print(f"{left_name} numeric records:", len(left_keys))
    print(f"{right_name} numeric records:", len(right_keys))
    print("Matched state-month series:", len(matched))
    print(f"{left_name} without matching {right_name}:",
          len(left_keys) - len(matched))
    print(f"{right_name} without matching {left_name}:",
          len(right_keys) - len(matched))


compare_coverage(capacity, generation, "Capacity", "Generation")
compare_coverage(generation, emissions, "Generation", "Emissions")
