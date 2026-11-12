
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"

INPUT_FILE = OUTPUT_DIR / "national_month_analysis.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_VARIABLES = [
    "Total Generation",
    "Renewables",
    "Fossil",
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other Renewables",
]

RENEWABLE_SOURCES = [
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other Renewables",
]

SOURCE_ANNUAL_COLUMNS = {
    "Solar": "Solar_GWh",
    "Wind": "Wind_GWh",
    "Hydro": "Hydro_GWh",
    "Bioenergy": "Bioenergy_GWh",
    "Other Renewables": "Other_Renewables_GWh",
}

RECONCILIATION_TOLERANCE = 1e-6


# ============================================================
# 2. LOAD AND VALIDATE NATIONAL DATA
# ============================================================

print("=" * 70)
print("A1: NATIONAL GENERATION ANALYSIS")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}\n"
        "Run 03_build_analysis_dataset.py first."
    )

df = pd.read_csv(INPUT_FILE)

# Actual schema uses Month, not Date.
if "Month" not in df.columns:
    raise ValueError(
        "Expected a 'Month' column. "
        f"Available columns: {df.columns.tolist()}"
    )

if "State" not in df.columns:
    raise ValueError("Expected a State column.")

# Confirm that this is the India Total national dataset.
states = df["State"].dropna().unique()

if len(states) != 1 or states[0] != "India Total":
    raise ValueError(
        f"Expected only 'India Total', found: {states.tolist()}"
    )

# Convert YYYY-MM into a datetime column for analysis and plotting.
df["Date"] = pd.to_datetime(
    df["Month"].astype(str) + "-01",
    format="%Y-%m-%d",
    errors="coerce"
)

if df["Date"].isna().any():
    raise ValueError("Some Month values could not be parsed.")

df = df.sort_values("Date").reset_index(drop=True)

missing_columns = [
    col for col in REQUIRED_VARIABLES
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Required generation columns missing: {missing_columns}"
    )

if df["Date"].duplicated().any():
    raise ValueError("Duplicate national months found.")

# Expected national period: January 2019 to November 2025.
expected_dates = pd.date_range(
    start="2019-01-01",
    end="2025-11-01",
    freq="MS"
)

if not pd.DatetimeIndex(df["Date"]).equals(expected_dates):
    raise ValueError(
        "Expected a continuous monthly period from "
        "January 2019 to November 2025."
    )

if len(df) != 83:
    raise ValueError(
        f"Expected 83 monthly rows, found {len(df)}."
    )

# Convert required generation fields to numeric.
for col in REQUIRED_VARIABLES:
    df[col] = pd.to_numeric(df[col], errors="coerce")

missing_values = df[REQUIRED_VARIABLES].isna().sum()

if missing_values.sum() > 0:
    raise ValueError(
        "Missing or non-numeric values found in required fields:\n"
        f"{missing_values[missing_values > 0]}"
    )

if (df[REQUIRED_VARIABLES] < 0).any().any():
    raise ValueError("Negative generation values found.")

if (df["Total Generation"] <= 0).any():
    raise ValueError("Total Generation contains zero or negative values.")

if (df["Renewables"] <= 0).any():
    raise ValueError(
        "Renewables contains zero or negative values. "
        "Check before calculating source shares."
    )

print(f"National record: {states[0]}")
print(f"Input rows: {len(df):,}")
print(f"Period: {df['Date'].min():%Y-%m} to {df['Date'].max():%Y-%m}")
print("Required fields: complete")
print("Duplicate months: 0")
print("Negative generation values: 0")


# ============================================================
# 3. MONTHLY GENERATION METRICS
# ============================================================

monthly = df[["Date", "Month"] + REQUIRED_VARIABLES].copy()

monthly["Year"] = monthly["Date"].dt.year
monthly["Month_Number"] = monthly["Date"].dt.month
monthly["Month_Name"] = monthly["Date"].dt.strftime("%b")

# Main generation shares.
monthly["Renewable Share (%)"] = (
    monthly["Renewables"]
    / monthly["Total Generation"] * 100
)

monthly["Fossil Share (%)"] = (
    monthly["Fossil"]
    / monthly["Total Generation"] * 100
)

# Individual renewable sources as a share of total generation.
for source in RENEWABLE_SOURCES:
    monthly[f"{source} Share of Total (%)"] = (
        monthly[source]
        / monthly["Total Generation"] * 100
    )

# Individual renewable sources as a share of renewable generation.
for source in RENEWABLE_SOURCES:
    monthly[f"{source} Share of Renewables (%)"] = (
        monthly[source]
        / monthly["Renewables"] * 100
    )

# Year-on-year change: compare with the same month in the previous year.
# Undefined when the previous-year baseline is zero or unavailable.
yoy_variables = [
    "Total Generation",
    "Renewables",
    "Fossil",
] + RENEWABLE_SOURCES

for variable in yoy_variables:
    previous_year = monthly[variable].shift(12)

    monthly[f"{variable} YoY Change (%)"] = (
        (monthly[variable] - previous_year)
        / previous_year.where(previous_year > 0)
        * 100
    )


# ============================================================
# 4. RENEWABLE SOURCE RECONCILIATION
# ============================================================

# Compare the sum of individual renewable sources with
# Ember's reported Renewables aggregate.

monthly["Renewable Sources Sum"] = monthly[
    RENEWABLE_SOURCES
].sum(axis=1)

monthly["Renewable Reconciliation Difference"] = (
    monthly["Renewables"]
    - monthly["Renewable Sources Sum"]
)

monthly["Renewable Reconciliation Match"] = (
    monthly["Renewable Reconciliation Difference"].abs()
    <= RECONCILIATION_TOLERANCE
)

reconciliation_matches = int(
    monthly["Renewable Reconciliation Match"].sum()
)

max_reconciliation_difference = float(
    monthly["Renewable Reconciliation Difference"].abs().max()
)


# ============================================================
# 5. ANNUAL SUMMARY
# ============================================================

# Sum monthly GWh to calculate annual generation.
# Calculate annual shares from annual totals, NOT averages
# of monthly percentages.

annual = (
    monthly.groupby("Year", as_index=False)
    .agg(
        Months_Observed=("Date", "count"),
        Total_Generation_GWh=("Total Generation", "sum"),
        Renewable_Generation_GWh=("Renewables", "sum"),
        Fossil_Generation_GWh=("Fossil", "sum"),
        Solar_GWh=("Solar", "sum"),
        Wind_GWh=("Wind", "sum"),
        Hydro_GWh=("Hydro", "sum"),
        Bioenergy_GWh=("Bioenergy", "sum"),
        Other_Renewables_GWh=("Other Renewables", "sum"),
    )
)

annual["Months_Expected"] = np.where(
    annual["Year"] == 2025, 11, 12
)

annual["Period_Status"] = np.where(
    annual["Months_Observed"] == 12,
    "Complete calendar year",
    "Partial year"
)

annual["Renewable Share (%)"] = (
    annual["Renewable_Generation_GWh"]
    / annual["Total_Generation_GWh"] * 100
)

annual["Fossil Share (%)"] = (
    annual["Fossil_Generation_GWh"]
    / annual["Total_Generation_GWh"] * 100
)

# Individual renewable sources as a percentage of annual
# renewable generation.
for source, column in SOURCE_ANNUAL_COLUMNS.items():
    annual[f"{source} Share of Renewables (%)"] = (
        annual[column]
        / annual["Renewable_Generation_GWh"] * 100
    )

annual.to_csv(
    OUTPUT_DIR / "04_annual_national_summary.csv",
    index=False
)


# ============================================================
# 6. SAVE MONTHLY METRICS
# ============================================================

monthly.to_csv(
    OUTPUT_DIR / "04_monthly_national_metrics.csv",
    index=False
)


# ============================================================
# 7. CHART 1 — MONTHLY GENERATION TRENDS
# ============================================================

fig, ax = plt.subplots(figsize=(13, 6))

ax.plot(
    monthly["Date"],
    monthly["Total Generation"],
    label="Total generation",
    linewidth=2
)

ax.plot(
    monthly["Date"],
    monthly["Renewables"],
    label="Renewable generation",
    linewidth=1.8
)

ax.plot(
    monthly["Date"],
    monthly["Fossil"],
    label="Fossil generation",
    linewidth=1.8
)

ax.set_title("India: Monthly Electricity Generation")
ax.set_xlabel("Month")
ax.set_ylabel("Generation (GWh)")
ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig(
    CHART_DIR / "04_01_monthly_generation_trends.png",
    dpi=200
)
plt.close(fig)


# ============================================================
# 8. CHART 2 — RENEWABLE AND FOSSIL SHARES
# ============================================================

fig, ax = plt.subplots(figsize=(13, 6))

ax.plot(
    monthly["Date"],
    monthly["Renewable Share (%)"],
    label="Renewable share",
    linewidth=2
)

ax.plot(
    monthly["Date"],
    monthly["Fossil Share (%)"],
    label="Fossil share",
    linewidth=2
)

ax.set_title(
    "India: Renewable and Fossil Share of Total Generation"
)
ax.set_xlabel("Month")
ax.set_ylabel("Share of total generation (%)")
ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig(
    CHART_DIR / "04_02_monthly_generation_shares.png",
    dpi=200
)
plt.close(fig)


# ============================================================
# 9. CHART 3 — ANNUAL RENEWABLE SHARE
# ============================================================

fig, ax = plt.subplots(figsize=(11, 6))

ax.bar(
    annual["Year"].astype(str),
    annual["Renewable Share (%)"]
)

ax.set_title(
    "India: Annual Renewable Share of Electricity Generation"
)
ax.set_xlabel("Year")
ax.set_ylabel("Renewable share (%)")
ax.grid(axis="y", alpha=0.3)

# Mark the partial 2025 period.
for index, row in annual.iterrows():
    if row["Period_Status"] == "Partial year":
        ax.text(
            index,
            row["Renewable Share (%)"],
            "Jan-Nov",
            ha="center",
            va="bottom",
            fontsize=9
        )

fig.tight_layout()
fig.savefig(
    CHART_DIR / "04_03_annual_renewable_share.png",
    dpi=200
)
plt.close(fig)


# ============================================================
# 10. CHART 4 — INDIVIDUAL RENEWABLE SOURCES
# ============================================================

fig, ax = plt.subplots(figsize=(13, 6))

for source in RENEWABLE_SOURCES:
    ax.plot(
        monthly["Date"],
        monthly[source],
        label=source,
        linewidth=1.6
    )

ax.set_title("India: Monthly Generation by Renewable Source")
ax.set_xlabel("Month")
ax.set_ylabel("Generation (GWh)")
ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig(
    CHART_DIR / "04_04_renewable_source_trends.png",
    dpi=200
)
plt.close(fig)


# ============================================================
# 11. SAVE VALIDATION AND RESULTS REPORT
# ============================================================

report_lines = [
    "=" * 70,
    "A1: NATIONAL GENERATION ANALYSIS REPORT",
    "=" * 70,
    "",
    "DATA VALIDATION",
    f"National record: {states[0]}",
    f"Monthly rows: {len(monthly)}",
    (
        f"Period: {monthly['Date'].min():%Y-%m} "
        f"to {monthly['Date'].max():%Y-%m}"
    ),
    "Required fields: complete",
    "Duplicate months: 0",
    "Negative generation values: 0",
    "",
    "RENEWABLE SOURCE RECONCILIATION",
    (
        f"Months matching aggregate: "
        f"{reconciliation_matches}/{len(monthly)}"
    ),
    (
        f"Maximum absolute difference (GWh): "
        f"{max_reconciliation_difference:.10f}"
    ),
    "",
    "ANNUAL SUMMARY",
    annual.to_string(index=False),
    "",
    "LATEST MONTH — NOVEMBER 2025",
    monthly.tail(1).to_string(index=False),
    "",
    "OUTPUT FILES",
    "04_monthly_national_metrics.csv",
    "04_annual_national_summary.csv",
    "04_national_generation_report.txt",
    "charts/04_01_monthly_generation_trends.png",
    "charts/04_02_monthly_generation_shares.png",
    "charts/04_03_annual_renewable_share.png",
    "charts/04_04_renewable_source_trends.png",
]

report = "\n".join(report_lines)

report_file = OUTPUT_DIR / "04_national_generation_report.txt"

report_file.write_text(
    report,
    encoding="utf-8"
)

print("\n" + report)
print("\nAnalysis completed successfully.")
