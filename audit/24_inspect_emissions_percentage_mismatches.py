
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"])

# Reported percentage values
pct = df[
    (df["Category"] == "Power sector emissions") &
    (df["Unit"] == "%")
][
    ["State", "Date", "Subcategory", "Variable", "Value"]
].rename(columns={"Value": "Reported_pct"})

# Corresponding absolute emissions values
absolute = df[
    (df["Category"] == "Power sector emissions") &
    (df["Unit"] == "ktCO2") &
    (df["Subcategory"].isin(["Fuel", "Aggregate fuel"]))
][
    ["State", "Date", "Subcategory", "Variable", "Value"]
].rename(columns={"Value": "Absolute_ktCO2"})

# Total emissions denominator
total = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "Total") &
    (df["Variable"] == "Total emissions") &
    (df["Unit"] == "ktCO2")
][
    ["State", "Date", "Value"]
].rename(columns={"Value": "Total_ktCO2"})

# Match the three datasets
result = pct.merge(
    absolute,
    on=["State", "Date", "Subcategory", "Variable"],
    how="left",
    validate="one_to_one"
)

result = result.merge(
    total,
    on=["State", "Date"],
    how="left",
    validate="many_to_one"
)

# Calculate percentage and difference
result = result[
    result["Reported_pct"].notna() &
    result["Absolute_ktCO2"].notna() &
    result["Total_ktCO2"].notna() &
    (result["Total_ktCO2"] > 0)
].copy()

result["Calculated_pct"] = (
    result["Absolute_ktCO2"] / result["Total_ktCO2"] * 100
)

result["Difference_pp"] = (
    result["Reported_pct"] - result["Calculated_pct"]
).abs()

# Inspect representative series
checks = [
    ("Fuel", "Solar"),
    ("Fuel", "Coal"),
    ("Aggregate fuel", "Clean")
]

for subcategory, variable in checks:
    sample = result[
        (result["Subcategory"] == subcategory) &
        (result["Variable"] == variable)
    ].copy()

    print(f"\n=== {subcategory}: {variable} ===")
    print("Comparable records:", len(sample))

    print(
        sample.nlargest(3, "Difference_pp")[
            [
                "State",
                "Date",
                "Reported_pct",
                "Absolute_ktCO2",
                "Total_ktCO2",
                "Calculated_pct",
                "Difference_pp"
            ]
        ].to_string(index=False)
    )

print("\n=== EMISSIONS PERCENTAGE RECONCILIATION: INDIA TOTAL VS STATES ===")

for label, data in [
    ("India Total", result[result["State"] == "India Total"]),
    ("Other states/UTs", result[result["State"] != "India Total"])
]:
    print(f"\n{label}")
    print("Comparable records:", len(data))
    print("Within 0.05 pp:", (data["Difference_pp"] <= 0.05).sum())
    print("Above 0.05 pp:", (data["Difference_pp"] > 0.05).sum())
    print("Median difference:", data["Difference_pp"].median())
    print("Maximum difference:", data["Difference_pp"].max())

print("\n=== NON-INDIA-TOTAL EMISSIONS MISMATCHES ===")

states = result[result["State"] != "India Total"].copy()

print("\nFive largest differences:")
print(
    states.nlargest(5, "Difference_pp")[
        [
            "State",
            "Date",
            "Subcategory",
            "Variable",
            "Reported_pct",
            "Absolute_ktCO2",
            "Total_ktCO2",
            "Calculated_pct",
            "Difference_pp"
        ]
    ].to_string(index=False)
)

print("\n=== REPORTED PERCENTAGE VS ABSOLUTE VALUE ===")

exact_matches = (
    states["Reported_pct"].sub(states["Absolute_ktCO2"]).abs() < 1e-9
)

print("Non-India comparable records:", len(states))
print("Exact reported/absolute matches:", exact_matches.sum())
print("Not exact matches:", (~exact_matches).sum())
