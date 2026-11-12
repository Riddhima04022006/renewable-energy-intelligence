
from pathlib import Path
import pandas as pd
import numpy as np

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
BASE_DIR = Path(r"D:\Renewable energy intelligence platform")
SOURCE_FILE = BASE_DIR / "india_monthly.csv"
GENERATION_FILE = (
    BASE_DIR / "analysis" / "outputs" / "state_month_analysis.csv"
)
OUTPUT_DIR = BASE_DIR / "analysis" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
START_MONTH = pd.Period("2021-07", freq="M")
END_MONTH = pd.Period("2025-11", freq="M")

# ------------------------------------------------------------
# LOAD SOURCE DATA
# ------------------------------------------------------------
df = pd.read_csv(SOURCE_FILE)

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df["Month"] = df["Date"].dt.to_period("M")

# ------------------------------------------------------------
# EXTRACT TOTAL EMISSIONS
# ------------------------------------------------------------
emissions = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "Total") &
    (df["Variable"] == "Total emissions") &
    (df["Unit"] == "ktCO2") &
    (~df["State"].isin(["India Total", "Others"]))
].copy()

emissions = emissions[
    ["State", "Month", "Value"]
].rename(columns={"Value": "Total_Emissions_ktCO2"})

# ------------------------------------------------------------
# EXTRACT REPORTED CO2 INTENSITY
# ------------------------------------------------------------
intensity = df[
    (df["Category"] == "Power sector emissions") &
    (df["Subcategory"] == "CO2 intensity") &
    (df["Variable"] == "CO2 intensity") &
    (df["Unit"] == "gCO2/kWh") &
    (~df["State"].isin(["India Total", "Others"]))
].copy()

intensity = intensity[
    ["State", "Month", "Value"]
].rename(columns={"Value": "Reported_CO2_Intensity_gCO2_kWh"})

# ------------------------------------------------------------
# EXTRACT TOTAL GENERATION
# ------------------------------------------------------------
generation = df[
    (df["Category"] == "Electricity generation") &
    (df["Subcategory"] == "Total") &
    (df["Variable"] == "Total Generation") &
    (df["Unit"] == "GWh") &
    (~df["State"].isin(["India Total", "Others"]))
].copy()

generation = generation[
    ["State", "Month", "Value"]
].rename(columns={"Value": "Total_Generation_GWh"})

# ------------------------------------------------------------
# VALIDATE SOURCE KEYS
# ------------------------------------------------------------
for name, data in [
    ("Emissions", emissions),
    ("CO2 intensity", intensity),
    ("Generation", generation),
]:
    duplicates = data.duplicated(["State", "Month"]).sum()

    if duplicates:
        raise ValueError(
            f"{name} has {duplicates} duplicate State-Month records."
        )

# ------------------------------------------------------------
# MERGE
# ------------------------------------------------------------
analysis = emissions.merge(
    intensity,
    on=["State", "Month"],
    how="outer",
    validate="one_to_one"
)

analysis = analysis.merge(
    generation,
    on=["State", "Month"],
    how="outer",
    validate="one_to_one"
)

# Common comparison period
analysis = analysis[
    (analysis["Month"] >= START_MONTH) &
    (analysis["Month"] <= END_MONTH)
].copy()

analysis = analysis.sort_values(
    ["State", "Month"]
).reset_index(drop=True)

# ------------------------------------------------------------
# INPUT VALIDATION
# ------------------------------------------------------------
expected_rows = 36 * 53

if len(analysis) != expected_rows:
    raise ValueError(
        f"Expected {expected_rows} rows, found {len(analysis)}."
    )

if analysis.duplicated(["State", "Month"]).any():
    raise ValueError("Duplicate State-Month records after merging.")

required = [
    "Total_Emissions_ktCO2",
    "Reported_CO2_Intensity_gCO2_kWh",
    "Total_Generation_GWh",
]

missing_counts = analysis[required].isna().sum()

if missing_counts.any():
    raise ValueError(
        "Missing required values in common-period analysis:\n"
        + missing_counts.to_string()
    )

if (analysis["Total_Generation_GWh"] <= 0).any():
    raise ValueError("Non-positive total generation encountered.")

# ------------------------------------------------------------
# CALCULATED INTENSITY CROSS-CHECK
# ------------------------------------------------------------
# Unit conversion:
# ktCO2 / GWh * 1000 = gCO2/kWh

analysis["Calculated_CO2_Intensity_gCO2_kWh"] = (
    analysis["Total_Emissions_ktCO2"] /
    analysis["Total_Generation_GWh"] * 1000
)

analysis["Intensity_Absolute_Difference"] = (
    analysis["Reported_CO2_Intensity_gCO2_kWh"] -
    analysis["Calculated_CO2_Intensity_gCO2_kWh"]
).abs()

# ------------------------------------------------------------
# PERIOD SUMMARY BY STATE
# ------------------------------------------------------------
period_summary = (
    analysis.groupby("State")
    .apply(
        lambda group: pd.Series({
            "Months": group["Month"].nunique(),
            "Total_Emissions_ktCO2":
                group["Total_Emissions_ktCO2"].sum(),
            "Total_Generation_GWh":
                group["Total_Generation_GWh"].sum(),
            "Generation_Weighted_CO2_Intensity_gCO2_kWh":
                (
                    group["Reported_CO2_Intensity_gCO2_kWh"] *
                    group["Total_Generation_GWh"]
                ).sum() / group["Total_Generation_GWh"].sum(),
            "Calculated_Period_CO2_Intensity_gCO2_kWh":
                (
                    group["Total_Emissions_ktCO2"].sum() /
                    group["Total_Generation_GWh"].sum() * 1000
                ),
        }),
        include_groups=False
    )
    .reset_index()
)

period_summary = period_summary.sort_values(
    "Total_Emissions_ktCO2",
    ascending=False
).reset_index(drop=True)

period_summary["Emissions_Rank"] = (
    period_summary["Total_Emissions_ktCO2"]
    .rank(method="min", ascending=False)
    .astype(int)
)

period_summary["Intensity_Rank"] = (
    period_summary[
        "Generation_Weighted_CO2_Intensity_gCO2_kWh"
    ]
    .rank(method="min", ascending=False)
    .astype(int)
)

# ------------------------------------------------------------
# ANNUAL STATE SUMMARY
# ------------------------------------------------------------
analysis["Year"] = analysis["Month"].dt.year

annual_summary = (
    analysis.groupby(["State", "Year"])
    .apply(
        lambda group: pd.Series({
            "Months": group["Month"].nunique(),
            "Total_Emissions_ktCO2":
                group["Total_Emissions_ktCO2"].sum(),
            "Total_Generation_GWh":
                group["Total_Generation_GWh"].sum(),
            "Generation_Weighted_CO2_Intensity_gCO2_kWh":
                (
                    group["Reported_CO2_Intensity_gCO2_kWh"] *
                    group["Total_Generation_GWh"]
                ).sum() / group["Total_Generation_GWh"].sum(),
        }),
        include_groups=False
    )
    .reset_index()
)

annual_summary["Period_Status"] = np.where(
    annual_summary["Months"] == 12,
    "Full year",
    "Partial year"
)

# ------------------------------------------------------------
# LIKE-FOR-LIKE JAN-NOV 2024 VS JAN-NOV 2025
# ------------------------------------------------------------
comparison = analysis[
    analysis["Month"].astype(str).str[-2:].astype(int).between(1, 11)
    & analysis["Year"].isin([2024, 2025])
].copy()

comparison["Comparison_Year"] = comparison["Year"]

comparison_summary = (
    comparison.groupby(["State", "Comparison_Year"])
    .apply(
        lambda group: pd.Series({
            "Months": group["Month"].nunique(),
            "Total_Emissions_ktCO2":
                group["Total_Emissions_ktCO2"].sum(),
            "Total_Generation_GWh":
                group["Total_Generation_GWh"].sum(),
            "Generation_Weighted_CO2_Intensity_gCO2_kWh":
                (
                    group["Reported_CO2_Intensity_gCO2_kWh"] *
                    group["Total_Generation_GWh"]
                ).sum() / group["Total_Generation_GWh"].sum(),
        }),
        include_groups=False
    )
    .reset_index()
)

comparison_wide = comparison_summary.pivot(
    index="State",
    columns="Comparison_Year",
    values=[
        "Total_Emissions_ktCO2",
        "Total_Generation_GWh",
        "Generation_Weighted_CO2_Intensity_gCO2_kWh",
    ]
)

comparison_wide.columns = [
    f"{metric}_{year}" for metric, year in comparison_wide.columns
]

comparison_wide = comparison_wide.reset_index()

for metric in [
    "Total_Emissions_ktCO2",
    "Total_Generation_GWh",
    "Generation_Weighted_CO2_Intensity_gCO2_kWh",
]:
    comparison_wide[f"{metric}_Change_Pct"] = (
        (
            comparison_wide[f"{metric}_2025"] -
            comparison_wide[f"{metric}_2024"]
        ) /
        comparison_wide[f"{metric}_2024"].replace(0, np.nan)
    ) * 100

# ------------------------------------------------------------
# SAVE OUTPUTS
# ------------------------------------------------------------
analysis["Month"] = analysis["Month"].astype(str)
annual_summary = annual_summary.sort_values(
    ["State", "Year"]
)

monthly_file = OUTPUT_DIR / "15_monthly_state_emissions.csv"
period_file = OUTPUT_DIR / "15_state_period_emissions_summary.csv"
annual_file = OUTPUT_DIR / "15_annual_state_emissions_summary.csv"
comparison_file = OUTPUT_DIR / "15_state_emissions_2024_2025_comparison.csv"
report_file = OUTPUT_DIR / "15_state_emissions_report.txt"

analysis.to_csv(monthly_file, index=False)
period_summary.to_csv(period_file, index=False)
annual_summary.to_csv(annual_file, index=False)
comparison_wide.to_csv(comparison_file, index=False)

# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------
lines = []

lines.append("=" * 70)
lines.append("A4.3: STATE-LEVEL EMISSIONS ANALYSIS")
lines.append("=" * 70)

lines.append("\nINPUT VALIDATION")
lines.append("-" * 70)
lines.append(f"State-month rows: {len(analysis)}")
lines.append(f"States/UTs: {analysis['State'].nunique()}")
lines.append(f"Months: {analysis['Month'].nunique()}")
lines.append(f"Period: {analysis['Month'].min()} to {analysis['Month'].max()}")
lines.append(
    f"Duplicate state-month keys: "
    f"{analysis.duplicated(['State', 'Month']).sum()}"
)
lines.append("\nMissing required values:")
lines.append(missing_counts.to_string())

lines.append("\nINTENSITY CROSS-CHECK")
lines.append("-" * 70)
lines.append(
    "Maximum absolute difference between reported and calculated "
    "monthly intensity: "
    f"{analysis['Intensity_Absolute_Difference'].max():.6f} gCO2/kWh"
)

lines.append("\nTOP 10 STATES BY TOTAL EMISSIONS")
lines.append("-" * 70)
lines.append(
    period_summary[
        [
            "State",
            "Total_Emissions_ktCO2",
            "Generation_Weighted_CO2_Intensity_gCO2_kWh",
            "Emissions_Rank",
        ]
    ].head(10).to_string(index=False)
)

lines.append("\nTOP 10 STATES BY GENERATION-WEIGHTED CO2 INTENSITY")
lines.append("-" * 70)
lines.append(
    period_summary.sort_values(
        "Generation_Weighted_CO2_Intensity_gCO2_kWh",
        ascending=False
    )[
        [
            "State",
            "Generation_Weighted_CO2_Intensity_gCO2_kWh",
            "Total_Emissions_ktCO2",
            "Intensity_Rank",
        ]
    ].head(10).to_string(index=False)
)

lines.append("\nJAN-NOV 2024 VS JAN-NOV 2025")
lines.append("-" * 70)
lines.append(
    comparison_wide.sort_values(
        "Total_Emissions_ktCO2_Change_Pct",
        ascending=False
    )[
        [
            "State",
            "Total_Emissions_ktCO2_Change_Pct",
            "Generation_Weighted_CO2_Intensity_gCO2_kWh_Change_Pct",
        ]
    ].to_string(index=False)
)

lines.append("\nOUTPUT FILES")
lines.append("-" * 70)
for path in [
    monthly_file,
    period_file,
    annual_file,
    comparison_file,
]:
    lines.append(str(path))

report_file.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print("\nA4.3 analysis completed successfully.")
