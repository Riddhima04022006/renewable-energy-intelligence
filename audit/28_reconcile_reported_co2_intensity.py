
import pandas as pd

# Read the dataset
df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# --------------------------------------------------
# 1. Extract reported CO2 intensity
# --------------------------------------------------

reported = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "CO2 intensity")
].copy()

print("=== REPORTED CO2 INTENSITY SERIES ===")
print("Variables:", reported["Variable"].unique())
print("Units:", reported["Unit"].unique())

# --------------------------------------------------
# 2. Extract total emissions
# --------------------------------------------------

emissions = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "Total") &
    (df["Variable"] == "Total emissions") &
    (df["Unit"] == "ktCO2")
][["State", "Date", "Value"]].copy()

emissions = emissions.rename(
    columns={"Value": "Emissions_ktCO2"}
)

# --------------------------------------------------
# 3. Extract total electricity generation
# --------------------------------------------------

generation = df[
    (df["Category"] == "Electricity generation") &
    (df["Subcategory"] == "Total") &
    (df["Variable"] == "Total Generation") &
    (df["Unit"] == "GWh")
][["State", "Date", "Value"]].copy()

generation = generation.rename(
    columns={"Value": "Generation_GWh"}
)

# --------------------------------------------------
# 4. Prepare reported intensity
# --------------------------------------------------

reported = reported[
    reported["Unit"] == "gCO2/kWh"
][["State", "Date", "Value"]].copy()

reported = reported.rename(
    columns={"Value": "Reported_Intensity"}
)

# Check whether each table has unique State-Date keys
for name, data in [
    ("Reported intensity", reported),
    ("Emissions", emissions),
    ("Generation", generation)
]:
    duplicates = data.duplicated(["State", "Date"]).sum()
    print(f"{name} duplicate keys: {duplicates}")

# --------------------------------------------------
# 5. Match the three measurements
# --------------------------------------------------

data = reported.merge(
    emissions,
    on=["State", "Date"],
    how="inner"
)

data = data.merge(
    generation,
    on=["State", "Date"],
    how="inner"
)

print("\n=== MATCHING SUMMARY ===")
print("Matched records:", len(data))

# --------------------------------------------------
# 6. Calculate independent CO2 intensity
# --------------------------------------------------

valid = data[
    data["Reported_Intensity"].notna() &
    data["Emissions_ktCO2"].notna() &
    data["Generation_GWh"].notna() &
    (data["Generation_GWh"] > 0)
].copy()

valid["Calculated_Intensity"] = (
    valid["Emissions_ktCO2"] /
    valid["Generation_GWh"]
) * 1000

valid["Absolute_Difference"] = (
    valid["Reported_Intensity"] -
    valid["Calculated_Intensity"]
).abs()

# --------------------------------------------------
# 7. Reconciliation results
# --------------------------------------------------

tolerance = 0.05

print("\n=== RECONCILIATION RESULTS ===")
print("Valid comparisons:", len(valid))
print("Unavailable comparisons:", len(data) - len(valid))
print("Within tolerance (0.05 gCO2/kWh):",
      (valid["Absolute_Difference"] <= tolerance).sum())
print("Beyond tolerance:",
      (valid["Absolute_Difference"] > tolerance).sum())

if len(valid) > 0:
    print("\n=== DIFFERENCE DISTRIBUTION ===")
    print("Median absolute difference:",
          valid["Absolute_Difference"].median())
    print("95th percentile:",
          valid["Absolute_Difference"].quantile(0.95))
    print("Maximum absolute difference:",
          valid["Absolute_Difference"].max())

    print("\n=== RESULTS BY STATE TYPE ===")
    print(
        valid.assign(
            Match=valid["Absolute_Difference"] <= tolerance
        )
        .groupby(valid["State"].eq("India Total").map({
            True: "India Total",
            False: "States/UTs"
        }))
        .agg(
            comparable=("Absolute_Difference", "count"),
            median_difference=("Absolute_Difference", "median"),
            p95_difference=("Absolute_Difference",
                            lambda x: x.quantile(0.95)),
            within_tolerance=("Match", "sum")
        )
    )
