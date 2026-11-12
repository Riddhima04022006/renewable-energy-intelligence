
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

tests = [
    ("Capacity", "MW", "Aggregate fuel", "Wind and Solar",
     [("Fuel", "Wind"), ("Fuel", "Solar")]),

    ("Capacity", "MW", "Aggregate fuel",
     "Hydro, Bioenergy and Other Renewables",
     [("Fuel", "Hydro"), ("Fuel", "Bioenergy"),
      ("Fuel", "Other Renewables")]),

    ("Capacity", "MW", "Aggregate fuel", "Gas and Other Fossil",
     [("Fuel", "Gas"), ("Fuel", "Other Fossil")]),

    ("Capacity", "MW", "Aggregate fuel", "Renewables",
     [("Fuel", "Solar"), ("Fuel", "Wind"), ("Fuel", "Hydro"),
      ("Fuel", "Bioenergy"), ("Fuel", "Other Renewables")]),

    ("Capacity", "MW", "Aggregate fuel", "Fossil",
     [("Fuel", "Coal"), ("Fuel", "Gas"), ("Fuel", "Other Fossil")]),

    ("Capacity", "MW", "Aggregate fuel", "Clean",
     [("Aggregate fuel", "Renewables"), ("Fuel", "Nuclear")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Wind and Solar",
     [("Fuel", "Wind"), ("Fuel", "Solar")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Hydro, Bioenergy and Other Renewables",
     [("Fuel", "Hydro"), ("Fuel", "Bioenergy"),
      ("Fuel", "Other Renewables")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Gas and Other Fossil",
     [("Fuel", "Gas"), ("Fuel", "Other Fossil")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel",
     "Renewables",
     [("Fuel", "Solar"), ("Fuel", "Wind"), ("Fuel", "Hydro"),
      ("Fuel", "Bioenergy"), ("Fuel", "Other Renewables")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel", "Fossil",
     [("Fuel", "Coal"), ("Fuel", "Gas"), ("Fuel", "Other Fossil")]),

    ("Power sector emissions", "ktCO2", "Aggregate fuel", "Clean",
     [("Aggregate fuel", "Renewables"), ("Fuel", "Nuclear")]),

    ("Power sector emissions", "ktCO2", "Total", "Total emissions",
     [("Aggregate fuel", "Clean"), ("Aggregate fuel", "Fossil")])
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

    target = (subcategory, aggregate)
    required = [target] + components

    if any(key not in wide.columns for key in required):
        continue

    comparison = wide[required].dropna()

    difference = (
        comparison[target] -
        comparison[components].sum(axis=1)
    ).abs()

    matches = difference <= tolerance
    larger = difference > tolerance

    print(f"\n{category} | {aggregate}")
    print("Comparable:", len(comparison))
    print("Matches within tolerance:", int(matches.sum()))
    print("Differences beyond tolerance:", int(larger.sum()))
    print("Maximum absolute difference:", f"{difference.max():.12e}")
    print("Mean absolute difference:", f"{difference.mean():.12e}")

    print("Differences > 0.01:", int((difference > 0.01).sum()))
