
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

tests = [
    ("Capacity", "MW", "Aggregate fuel", "Clean",
     [("Aggregate fuel", "Renewables"), ("Fuel", "Nuclear")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel", "Clean",
     [("Aggregate fuel", "Renewables"), ("Fuel", "Nuclear")]),

    ("Power sector emissions", "ktCO2", "Total", "Total emissions",
     [("Aggregate fuel", "Clean"), ("Aggregate fuel", "Fossil")])
]

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
    required_keys = [target_key] + components

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

    component_sum = comparison[components].sum(axis=1)
    difference = comparison[target_key] - component_sum
    absolute_difference = difference.abs()

    print("Comparable state-months:", len(comparison))
    print("Unavailable comparisons:", unavailable)
    print("Exact matches:", int(absolute_difference.eq(0).sum()))
    print("Differences <= 0.01:", int(
        (absolute_difference.gt(0) &
         absolute_difference.le(0.01)).sum()
    ))
    print("Differences > 0.01:", int(
        absolute_difference.gt(0.01).sum()
    ))

    if len(comparison) > 0:
        print(
            "Mean absolute difference:",
            round(absolute_difference.mean(), 8)
        )
        print(
            "Maximum absolute difference:",
            round(absolute_difference.max(), 8)
        )
