
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

tests = [
    # Category, Unit, Aggregate subcategory, Aggregate, Components
    ("Capacity", "MW", "Aggregate fuel", "Wind and Solar",
     ["Wind", "Solar"]),

    ("Capacity", "MW", "Aggregate fuel",
     "Hydro, Bioenergy and Other Renewables",
     ["Hydro", "Bioenergy", "Other Renewables"]),

    ("Capacity", "MW", "Aggregate fuel", "Gas and Other Fossil",
     ["Gas", "Other Fossil"]),

    ("Capacity", "MW", "Aggregate fuel", "Renewables",
     ["Solar", "Wind", "Hydro", "Bioenergy", "Other Renewables"]),

    ("Capacity", "MW", "Aggregate fuel", "Fossil",
     ["Coal", "Gas", "Other Fossil"]),

    ("Capacity", "MW", "Aggregate fuel", "Clean",
     ["Renewables", "Nuclear"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Wind and Solar", ["Wind", "Solar"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Hydro, Bioenergy and Other Renewables",
     ["Hydro", "Bioenergy", "Other Renewables"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Gas and Other Fossil", ["Gas", "Other Fossil"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Renewables",
     ["Solar", "Wind", "Hydro", "Bioenergy", "Other Renewables"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Fossil", ["Coal", "Gas", "Other Fossil"]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Clean", ["Renewables", "Nuclear"]),

    ("Power sector emissions", "ktCO2", "Total",
     "Total emissions", ["Clean", "Fossil"])
]

tolerance = 1e-6

for category, unit, subcategory, aggregate, components in tests:

    subset = df[
        (df["Category"] == category) &
        (df["Unit"] == unit)
    ].copy()

    subset["Value"] = pd.to_numeric(
        subset["Value"], errors="coerce"
    )

    wide = subset.pivot_table(
        index=["State", "Date"],
        columns=["Subcategory", "Variable"],
        values="Value",
        aggfunc="first"
    )

    target_key = (subcategory, aggregate)
    component_keys = [("Fuel", name) for name in components]
    required_keys = [target_key] + component_keys

    print(f"\n{category} | {unit} | {aggregate}")

    missing_keys = [
        key for key in required_keys
        if key not in wide.columns
    ]

    if missing_keys:
        print("Required series not found:", missing_keys)
        continue

    comparison = wide[required_keys].dropna()
    unavailable = len(wide) - len(comparison)

    component_sum = comparison[component_keys].sum(axis=1)
    difference = comparison[target_key] - component_sum

    matches = difference.abs() <= tolerance

    print("Comparable state-months:", len(comparison))
    print("Matching:", int(matches.sum()))
    print("Discrepancies:", int((~matches).sum()))
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
