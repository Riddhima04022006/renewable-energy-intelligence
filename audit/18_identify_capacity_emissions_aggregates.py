
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

categories = [
    "Capacity",
    "Power sector emissions"
]

for category in categories:

    subset = df[df["Category"] == category]

    print(f"\n=== {category.upper()} ===")

    inventory = (
        subset[
            ["Subcategory", "Variable", "Unit"]
        ]
        .drop_duplicates()
        .sort_values(
            ["Subcategory", "Unit", "Variable"]
        )
    )

    for (subcategory, unit), group in inventory.groupby(
        ["Subcategory", "Unit"],
        sort=True
    ):
        variables = sorted(group["Variable"].unique())

        print(f"\n{subcategory} | {unit}")
        print("Variables:", ", ".join(variables))
