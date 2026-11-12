
import pandas as pd

# Load dataset
df = pd.read_csv("../india_monthly.csv")

# Convert values to numeric
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

# Keep electricity generation measured in GWh
df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

# Create a wide table using both Subcategory and Variable
wide = df.pivot(
    index=["State", "Date"],
    columns=["Subcategory", "Variable"],
    values="Value"
)

# Candidate aggregate relationships
checks = {
    "Wind and Solar": (
        "Aggregate fuel",
        [
            ("Fuel", "Wind"),
            ("Fuel", "Solar")
        ]
    ),
    "Bioenergy and Other Renewables": (
        "Aggregate fuel",
        [
            ("Fuel", "Bioenergy"),
            ("Fuel", "Other Renewables")
        ]
    ),
    "Hydro/Bioenergy and Other Renewables": (
        "Aggregate fuel",
        [
            ("Fuel", "Hydro"),
            ("Fuel", "Bioenergy"),
            ("Fuel", "Other Renewables")
        ]
    ),
    "Gas and Other Fossil": (
        "Aggregate fuel",
        [
            ("Fuel", "Gas"),
            ("Fuel", "Other Fossil")
        ]
    ),
    "Renewables": (
        "Aggregate fuel",
        [
            ("Fuel", "Solar"),
            ("Fuel", "Wind"),
            ("Fuel", "Hydro"),
            ("Fuel", "Bioenergy"),
            ("Fuel", "Other Renewables")
        ]
    ),
    "Fossil": (
        "Aggregate fuel",
        [
            ("Fuel", "Coal"),
            ("Fuel", "Gas"),
            ("Fuel", "Other Fossil")
        ]
    ),
    "Clean": (
        "Aggregate fuel",
        [
            ("Aggregate fuel", "Renewables"),
            ("Fuel", "Nuclear")
        ]
    ),
    "Total Generation": (
        "Total",
        [
            ("Aggregate fuel", "Clean"),
            ("Aggregate fuel", "Fossil")
        ]
    )
}

print("=== GENERATION AGGREGATE RECONCILIATION ===")

for aggregate, (aggregate_subcategory, components) in checks.items():

    aggregate_key = (aggregate_subcategory, aggregate)

    if aggregate_key not in wide.columns:
        print(f"\n{aggregate}: Aggregate variable not found")
        continue

    missing_components = [
        component for component in components
        if component not in wide.columns
    ]

    if missing_components:
        print(f"\n{aggregate}: Components not found: {missing_components}")
        continue

    # Aggregate value
    actual = wide[aggregate_key]

    # Sum of individual components
    expected = wide[components].sum(axis=1, min_count=len(components))

    # Compare only where all required values are available
    valid = actual.notna() & expected.notna()

    difference = actual[valid] - expected[valid]
    absolute_difference = difference.abs()

    tolerance = 1e-6

    matches = absolute_difference <= tolerance
    discrepancies = absolute_difference > tolerance

    print(f"\n{aggregate}")
    print(f"Comparable state-months: {valid.sum()}")
    print(f"Matching: {matches.sum()}")
    print(f"Discrepancies: {discrepancies.sum()}")
    print(f"Missing comparisons: {(~valid).sum()}")

    if valid.sum() > 0:
        print(
            f"Mean absolute difference: "
            f"{absolute_difference.mean():.6f} GWh"
        )
        print(
            f"Maximum absolute difference: "
            f"{absolute_difference.max():.6f} GWh"
        )
