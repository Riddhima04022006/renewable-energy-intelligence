
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

# Keep only electricity generation measured in GWh.
df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

# Each state-month is one comparison unit.
# Subcategory is retained because the same variable name
# can appear under different subcategories.
wide = df.pivot_table(
    index=["State", "Date"],
    columns=["Subcategory", "Variable"],
    values="Value",
    aggfunc="first"
)

# (Aggregate subcategory, aggregate variable, component variables)
tests = [
    (
        "Aggregate fuel", "Wind and Solar",
        ["Wind", "Solar"]
    ),
    (
        "Aggregate fuel", "Hydro, Bioenergy and Other Renewables",
        ["Hydro", "Bioenergy", "Other Renewables"]
    ),
    (
        "Aggregate fuel", "Gas and Other Fossil",
        ["Gas", "Other Fossil"]
    ),
    (
        "Aggregate fuel", "Renewables",
        ["Solar", "Wind", "Hydro", "Bioenergy", "Other Renewables"]
    ),
    (
        "Aggregate fuel", "Fossil",
        ["Coal", "Gas", "Other Fossil"]
    ),
    (
        "Aggregate fuel", "Clean",
        ["Renewables", "Nuclear"]
    ),
    (
        "Total", "Total Generation",
        ["Clean", "Fossil"]
    )
]

tolerance = 1e-6

print("=== GENERATION AGGREGATE RECONCILIATION ===")

for subcategory, aggregate, components in tests:

    target_key = (subcategory, aggregate)
    component_keys = [("Fuel", name) for name in components]

    required_keys = [target_key] + component_keys

    if any(key not in wide.columns for key in required_keys):
        missing_keys = [
            key for key in required_keys
            if key not in wide.columns
        ]
        print(f"\n{aggregate}")
        print("Required series not found:", missing_keys)
        continue

    comparison = wide[required_keys].dropna()

    unavailable = len(wide) - len(comparison)

    component_sum = comparison[component_keys].sum(axis=1)
    difference = comparison[target_key] - component_sum

    matches = difference.abs() <= tolerance
    discrepancies = ~matches

    print(f"\n{aggregate}")
    print("Comparable state-months:", len(comparison))
    print("Matching:", int(matches.sum()))
    print("Discrepancies:", int(discrepancies.sum()))
    print("Unavailable comparisons:", unavailable)

    if len(comparison) > 0:
        print(
            "Mean absolute difference:",
            round(difference.abs().mean(), 8)
        )
        print(
            "Maximum absolute difference:",
            round(difference.abs().max(), 8)
        )
