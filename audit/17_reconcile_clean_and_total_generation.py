
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

wide = df.pivot_table(
    index=["State", "Date"],
    columns=["Subcategory", "Variable"],
    values="Value",
    aggfunc="first"
)

tests = [
    (
        "Clean",
        ("Aggregate fuel", "Clean"),
        [
            ("Aggregate fuel", "Renewables"),
            ("Fuel", "Nuclear")
        ]
    ),
    (
        "Total Generation",
        ("Total", "Total Generation"),
        [
            ("Aggregate fuel", "Clean"),
            ("Aggregate fuel", "Fossil")
        ]
    )
]

tolerance = 1e-6

print("=== CLEAN AND TOTAL GENERATION RECONCILIATION ===")

for name, target_key, component_keys in tests:

    required_keys = [target_key] + component_keys

    missing_keys = [
        key for key in required_keys
        if key not in wide.columns
    ]

    print(f"\n{name}")

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
