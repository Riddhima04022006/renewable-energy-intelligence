
import pandas as pd

df = pd.read_csv("../india_monthly.csv")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

# --------------------------------------------------
# 1. Inspect exact aggregate names and subcategories
# --------------------------------------------------

print("=== RELEVANT VARIABLE NAMES ===")

terms = ["Bioenergy", "Other Renewables", "Hydro"]

relevant = df[
    df["Variable"].str.contains(
        "|".join(terms),
        case=False,
        na=False
    )
]

print(
    relevant[
        ["Subcategory", "Variable"]
    ]
    .drop_duplicates()
    .sort_values(["Subcategory", "Variable"])
    .to_string(index=False)
)

# --------------------------------------------------
# 2. Reconstruct the four relationships with
#    missing comparisons
# --------------------------------------------------

wide = df.pivot(
    index=["State", "Date"],
    columns=["Subcategory", "Variable"],
    values="Value"
)

checks = {
    "Gas and Other Fossil": (
        ("Aggregate fuel", "Gas and Other Fossil"),
        [
            ("Fuel", "Gas"),
            ("Fuel", "Other Fossil")
        ]
    ),
    "Fossil": (
        ("Aggregate fuel", "Fossil"),
        [
            ("Fuel", "Coal"),
            ("Fuel", "Gas"),
            ("Fuel", "Other Fossil")
        ]
    ),
    "Clean": (
        ("Aggregate fuel", "Clean"),
        [
            ("Aggregate fuel", "Renewables"),
            ("Fuel", "Nuclear")
        ]
    ),
    "Total Generation": (
        ("Total", "Total Generation"),
        [
            ("Aggregate fuel", "Clean"),
            ("Aggregate fuel", "Fossil")
        ]
    )
}

missing_records = []

for aggregate, (aggregate_key, components) in checks.items():

    actual = wide[aggregate_key]

    expected = wide[components].sum(
        axis=1,
        min_count=len(components)
    )

    missing = actual.isna() | expected.isna()

    for state, date in wide.index[missing]:
        missing_records.append({
            "Aggregate": aggregate,
            "State": state,
            "Date": date
        })

missing_df = pd.DataFrame(missing_records)

print("\n=== MISSING COMPARISONS BY AGGREGATE ===")

print(
    missing_df.groupby("Aggregate")
    .size()
    .to_string()
)

print("\n=== MISSING COMPARISONS BY STATE ===")

print(
    missing_df.groupby("State")
    .size()
    .sort_values(ascending=False)
    .to_string()
)

print("\n=== MISSING COMPARISONS BY YEAR ===")

missing_df["Year"] = pd.to_datetime(
    missing_df["Date"]
).dt.year

print(
    missing_df.groupby("Year")
    .size()
    .to_string()
)
