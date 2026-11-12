
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

checks = [
    {
        "category": "Electricity generation",
        "percentage_unit": "%",
        "absolute_unit": "GWh",
        "denominator_subcategory": "Total",
        "denominator_variable": "Total Generation"
    },
    {
        "category": "Power sector emissions",
        "percentage_unit": "%",
        "absolute_unit": "ktCO2",
        "denominator_subcategory": "Total",
        "denominator_variable": "Total emissions"
    }
]

for check in checks:

    category = check["category"]

    subset = df[df["Category"] == category]

    print(f"\n=== {category.upper()} ===")

    percentage = subset[
        subset["Unit"] == check["percentage_unit"]
    ]

    absolute = subset[
        subset["Unit"] == check["absolute_unit"]
    ]

    print("\nPERCENTAGE SERIES")

    inventory = (
        percentage.groupby(
            ["Subcategory", "Variable"]
        )
        .agg(
            rows=("Value", "size"),
            numeric_values=("Value", "count")
        )
        .reset_index()
        .sort_values(["Subcategory", "Variable"])
    )

    for _, row in inventory.iterrows():

        subcategory = row["Subcategory"]
        variable = row["Variable"]

        absolute_match = absolute[
            (absolute["Subcategory"] == subcategory) &
            (absolute["Variable"] == variable)
        ]

        absolute_numeric = absolute_match["Value"].count()

        print(
            f"{subcategory} | {variable}: "
            f"percentage numeric={row['numeric_values']}, "
            f"absolute numeric={absolute_numeric}"
        )

    print("\nTOTAL DENOMINATOR")

    denominator = subset[
        (subset["Subcategory"] == check["denominator_subcategory"]) &
        (subset["Variable"] == check["denominator_variable"]) &
        (subset["Unit"] == check["absolute_unit"])
    ]

    print("Variable:", check["denominator_variable"])
    print("Rows:", len(denominator))
    print("Numeric values:", denominator["Value"].count())
    print("Unique state-months:",
          denominator[["State", "Date"]].drop_duplicates().shape[0])
