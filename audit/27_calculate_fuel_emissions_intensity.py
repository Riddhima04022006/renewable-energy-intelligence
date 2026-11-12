
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Date"] = pd.to_datetime(df["Date"])
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

keys = ["State", "Date", "Variable"]

# Individual fuel generation
generation = df[
    (df["Category"] == "Electricity generation") &
    (df["Subcategory"] == "Fuel") &
    (df["Unit"] == "GWh")
][keys + ["Value"]].rename(
    columns={"Value": "Generation_GWh"}
)

# Individual fuel emissions
emissions = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "Fuel") &
    (df["Unit"] == "ktCO2")
][keys + ["Value"]].rename(
    columns={"Value": "Emissions_ktCO2"}
)

# Match generation and emissions
data = generation.merge(
    emissions,
    on=keys,
    how="inner",
    validate="one_to_one"
)

# Valid records require positive generation and non-negative emissions
valid = (
    data["Generation_GWh"].notna() &
    data["Emissions_ktCO2"].notna() &
    data["Generation_GWh"].gt(0) &
    data["Emissions_ktCO2"].ge(0)
)

data["Emissions_Intensity_gCO2_kWh"] = pd.NA

data.loc[valid, "Emissions_Intensity_gCO2_kWh"] = (
    data.loc[valid, "Emissions_ktCO2"] /
    data.loc[valid, "Generation_GWh"] * 1000
)

# Summary by fuel
summary = (
    data[valid]
    .groupby("Variable")
    .agg(
        comparable=("Emissions_Intensity_gCO2_kWh", "count"),
        median=("Emissions_Intensity_gCO2_kWh", "median"),
        p95=("Emissions_Intensity_gCO2_kWh",
             lambda x: x.quantile(0.95)),
        maximum=("Emissions_Intensity_gCO2_kWh", "max"),
        zero_emissions=("Emissions_ktCO2",
                        lambda x: (x == 0).sum())
    )
    .reset_index()
)

print("=== D7.2: FUEL-WISE EMISSIONS INTENSITY ===")

print("Matched records:", len(data))
print("Valid intensity records:", valid.sum())

print("Missing generation or emissions:",
      (data["Generation_GWh"].isna() |
       data["Emissions_ktCO2"].isna()).sum())

print("Zero generation records:",
      data["Generation_GWh"].eq(0).sum())

print("Negative generation/emissions records:",
      (
          data["Generation_GWh"].lt(0) |
          data["Emissions_ktCO2"].lt(0)
      ).sum())

print("\n=== RESULTS BY FUEL ===")
print(summary.round(4).to_string(index=False))
