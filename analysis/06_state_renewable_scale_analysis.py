
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# A2.1: RENEWABLE PENETRATION VS GENERATION SCALE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"

STATE_FILE = OUTPUT_DIR / "state_month_analysis.csv"
NATIONAL_FILE = OUTPUT_DIR / "national_month_analysis.csv"

START_MONTH = "2021-07"
END_MONTH = "2025-11"

RENEWABLE_COL = "Renewables"
TOTAL_COL = "Total Generation"

print("=" * 70)
print("A2.1: RENEWABLE PENETRATION VS GENERATION SCALE")
print("=" * 70)


# ------------------------------------------------------------
# 1. LOAD AND VALIDATE INPUTS
# ------------------------------------------------------------

if not STATE_FILE.exists():
    raise FileNotFoundError(f"Missing input file: {STATE_FILE}")

if not NATIONAL_FILE.exists():
    raise FileNotFoundError(f"Missing input file: {NATIONAL_FILE}")

states = pd.read_csv(STATE_FILE)
national = pd.read_csv(NATIONAL_FILE)

required_state = {"State", "Month", RENEWABLE_COL, TOTAL_COL}
required_national = {"State", "Month", RENEWABLE_COL, TOTAL_COL}

if not required_state.issubset(states.columns):
    raise ValueError(
        f"State dataset is missing columns: "
        f"{required_state - set(states.columns)}"
    )

if not required_national.issubset(national.columns):
    raise ValueError(
        f"National dataset is missing columns: "
        f"{required_national - set(national.columns)}"
    )

states["Month"] = states["Month"].astype(str)
national["Month"] = national["Month"].astype(str)

states = states[
    states["Month"].between(START_MONTH, END_MONTH)
].copy()

national = national[
    (national["State"] == "India Total")
    & national["Month"].between(START_MONTH, END_MONTH)
].copy()

for df in (states, national):
    df[RENEWABLE_COL] = pd.to_numeric(
        df[RENEWABLE_COL], errors="coerce"
    )
    df[TOTAL_COL] = pd.to_numeric(
        df[TOTAL_COL], errors="coerce"
    )

duplicate_count = states.duplicated(
    subset=["State", "Month"]
).sum()

missing_state_values = states[
    [RENEWABLE_COL, TOTAL_COL]
].isna().any(axis=1).sum()

missing_national_values = national[
    [RENEWABLE_COL, TOTAL_COL]
].isna().any(axis=1).sum()

if duplicate_count:
    raise ValueError(f"Duplicate state-month records: {duplicate_count}")

if missing_state_values:
    raise ValueError(
        f"Missing required state generation values: {missing_state_values}"
    )

if missing_national_values:
    raise ValueError(
        f"Missing required national generation values: {missing_national_values}"
    )

if (states[[RENEWABLE_COL, TOTAL_COL]] < 0).any().any():
    raise ValueError("Negative state generation values detected.")

if (national[[RENEWABLE_COL, TOTAL_COL]] < 0).any().any():
    raise ValueError("Negative national generation values detected.")

if (states[TOTAL_COL] <= 0).any():
    raise ValueError("Zero or negative state total-generation denominator.")

if (national[TOTAL_COL] <= 0).any():
    raise ValueError("Zero or negative national total-generation denominator.")

expected_months = 53

print("\nINPUT VALIDATION")
print("-" * 70)
print(f"State-month rows: {len(states):,}")
print(f"States / UTs: {states['State'].nunique()}")
print(f"Months: {states['Month'].nunique()}")
print(
    f"Period: {states['Month'].min()} to {states['Month'].max()}"
)
print(f"Duplicate state-month records: {duplicate_count}")
print(f"Missing state generation values: {missing_state_values}")
print(f"Missing national generation values: {missing_national_values}")
print(f"National months: {len(national)}")

if states["Month"].nunique() != expected_months:
    raise ValueError("Unexpected number of months in state dataset.")

if len(national) != expected_months:
    raise ValueError("National dataset does not contain all 53 months.")


# ------------------------------------------------------------
# 2. PERIOD-LEVEL STATE METRICS
# ------------------------------------------------------------

period = (
    states.groupby("State", as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum")
    )
)

period["Renewable_Share_Pct"] = (
    period["Renewable_Generation_GWh"]
    / period["Total_Generation_GWh"]
    * 100
)

india_renewable_gwh = national[RENEWABLE_COL].sum()
india_total_gwh = national[TOTAL_COL].sum()

period["National_Renewable_Contribution_Pct"] = (
    period["Renewable_Generation_GWh"]
    / india_renewable_gwh
    * 100
)

period["Renewable_Generation_Rank"] = (
    period["Renewable_Generation_GWh"]
    .rank(method="min", ascending=False)
    .astype(int)
)

period["Renewable_Share_Rank"] = (
    period["Renewable_Share_Pct"]
    .rank(method="min", ascending=False)
    .astype(int)
)

period["National_Contribution_Rank"] = (
    period["National_Renewable_Contribution_Pct"]
    .rank(method="min", ascending=False)
    .astype(int)
)

period = period.sort_values(
    "Renewable_Generation_GWh", ascending=False
).reset_index(drop=True)

period.to_csv(
    OUTPUT_DIR / "06_state_renewable_scale_ranking.csv",
    index=False
)

print("\nNATIONAL PERIOD TOTALS")
print("-" * 70)
print(f"India renewable generation: {india_renewable_gwh:,.2f} GWh")
print(f"India total generation: {india_total_gwh:,.2f} GWh")
print(
    "India renewable share: "
    f"{india_renewable_gwh / india_total_gwh * 100:.2f}%"
)

state_sum = period["Renewable_Generation_GWh"].sum()
print(f"Sum of state/UT renewable generation: {state_sum:,.2f} GWh")
print(
    "State/UT sum as percentage of India Total: "
    f"{state_sum / india_renewable_gwh * 100:.2f}%"
)

print("\nTOP 10 BY ABSOLUTE RENEWABLE GENERATION")
print("-" * 70)
print(
    period[
        [
            "State",
            "Renewable_Generation_GWh",
            "Total_Generation_GWh",
            "Renewable_Share_Pct",
            "National_Renewable_Contribution_Pct"
        ]
    ].head(10).round(2).to_string(index=False)
)

print("\nTOP 10 BY RENEWABLE SHARE")
print("-" * 70)
print(
    period.sort_values(
        "Renewable_Share_Pct", ascending=False
    )[
        [
            "State",
            "Renewable_Share_Pct",
            "Renewable_Generation_GWh",
            "Total_Generation_GWh"
        ]
    ].head(10).round(2).to_string(index=False)
)

print("\nTOP 10 CONTRIBUTIONS TO INDIA'S RENEWABLE GENERATION")
print("-" * 70)
print(
    period.sort_values(
        "National_Renewable_Contribution_Pct",
        ascending=False
    )[
        [
            "State",
            "National_Renewable_Contribution_Pct",
            "Renewable_Generation_GWh",
            "Renewable_Share_Pct"
        ]
    ].head(10).round(2).to_string(index=False)
)


# ------------------------------------------------------------
# 3. JAN-NOV 2024 VS JAN-NOV 2025
# ------------------------------------------------------------

comparison = states[
    states["Month"].str.startswith(("2024-", "2025-"))
].copy()

comparison["Year"] = comparison["Month"].str[:4]

comparison = comparison[
    comparison["Month"].str[5:7].astype(int).between(1, 11)
]

annual_period = (
    comparison.groupby(["State", "Year"], as_index=False)
    .agg(
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum"),
        Months_Observed=("Month", "nunique")
    )
)

annual_period["Renewable_Share_Pct"] = (
    annual_period["Renewable_Generation_GWh"]
    / annual_period["Total_Generation_GWh"]
    * 100
)

wide = annual_period.pivot(
    index="State",
    columns="Year",
    values=[
        "Renewable_Generation_GWh",
        "Total_Generation_GWh",
        "Renewable_Share_Pct",
        "Months_Observed"
    ]
)

wide.columns = [
    f"{metric}_{year}" for metric, year in wide.columns
]

wide = wide.reset_index()

for metric in [
    "Renewable_Generation_GWh",
    "Total_Generation_GWh",
    "Renewable_Share_Pct"
]:
    col_2024 = f"{metric}_2024"
    col_2025 = f"{metric}_2025"

    wide[f"{metric}_Change"] = wide[col_2025] - wide[col_2024]

    if metric != "Renewable_Share_Pct":
        wide[f"{metric}_Change_Pct"] = (
            wide[f"{metric}_Change"]
            / wide[col_2024].replace(0, pd.NA)
            * 100
        )

wide["Renewable_Share_Change_pp"] = (
    wide["Renewable_Share_Pct_Change"]
)

wide = wide.sort_values(
    "Renewable_Generation_GWh_Change", ascending=False
)

wide.to_csv(
    OUTPUT_DIR / "06_jan_nov_2024_2025_generation_scale_change.csv",
    index=False
)

print("\nJAN-NOV 2024 VS JAN-NOV 2025")
print("-" * 70)
print(
    "Sorted by absolute change in renewable generation (GWh)."
)
print(
    wide[
        [
            "State",
            "Renewable_Generation_GWh_2024",
            "Renewable_Generation_GWh_2025",
            "Renewable_Generation_GWh_Change",
            "Renewable_Generation_GWh_Change_Pct",
            "Renewable_Share_Pct_Change"
        ]
    ].round(2).to_string(index=False)
)


# ------------------------------------------------------------
# 4. ANNUAL STATE SUMMARY
# ------------------------------------------------------------

states_annual = states.copy()
states_annual["Year"] = states_annual["Month"].str[:4]

annual = (
    states_annual.groupby(["State", "Year"], as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum")
    )
)

annual["Renewable_Share_Pct"] = (
    annual["Renewable_Generation_GWh"]
    / annual["Total_Generation_GWh"]
    * 100
)

annual["Period_Status"] = annual.apply(
    lambda row: (
        "Complete calendar year"
        if row["Months_Observed"] == 12
        else "Partial year"
    ),
    axis=1
)

annual.to_csv(
    OUTPUT_DIR / "06_annual_state_generation_scale.csv",
    index=False
)


# ------------------------------------------------------------
# 5. CHARTS
# ------------------------------------------------------------

CHART_DIR.mkdir(parents=True, exist_ok=True)

# Chart 1: Top 10 states by renewable generation
top_generation = period.nlargest(
    10, "Renewable_Generation_GWh"
).sort_values("Renewable_Generation_GWh")

plt.figure(figsize=(11, 7))
plt.barh(
    top_generation["State"],
    top_generation["Renewable_Generation_GWh"]
)
plt.xlabel("Renewable generation (GWh)")
plt.ylabel("State / UT")
plt.title(
    "Top 10 States / UTs by Renewable Generation\n"
    "July 2021 – November 2025"
)
plt.tight_layout()
plt.savefig(
    CHART_DIR / "06_top_renewable_generation_states.png",
    dpi=200
)
plt.close()


# Chart 2: Renewable share vs renewable generation
plt.figure(figsize=(12, 8))
plt.scatter(
    period["Renewable_Generation_GWh"],
    period["Renewable_Share_Pct"]
)

for _, row in period.iterrows():
    if (
        row["Renewable_Generation_GWh"]
        >= period["Renewable_Generation_GWh"].nlargest(10).min()
        or row["Renewable_Share_Pct"] >= 90
    ):
        plt.annotate(
            row["State"],
            (
                row["Renewable_Generation_GWh"],
                row["Renewable_Share_Pct"]
            ),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points"
        )

plt.xlabel("Renewable generation (GWh)")
plt.ylabel("Renewable share (%)")
plt.title(
    "Renewable Penetration vs Renewable Generation Scale\n"
    "July 2021 – November 2025"
)
plt.tight_layout()
plt.savefig(
    CHART_DIR / "06_renewable_share_vs_generation.png",
    dpi=200
)
plt.close()


# Chart 3: Top 10 contributors to India's renewable generation
top_contribution = period.nlargest(
    10, "National_Renewable_Contribution_Pct"
).sort_values("National_Renewable_Contribution_Pct")

plt.figure(figsize=(11, 7))
plt.barh(
    top_contribution["State"],
    top_contribution["National_Renewable_Contribution_Pct"]
)
plt.xlabel("Contribution to India Total renewable generation (%)")
plt.ylabel("State / UT")
plt.title(
    "Top 10 State / UT Contributions to India's Renewable Generation\n"
    "July 2021 – November 2025"
)
plt.tight_layout()
plt.savefig(
    CHART_DIR / "06_top_national_renewable_contributors.png",
    dpi=200
)
plt.close()


# ------------------------------------------------------------
# 6. FINAL REPORT
# ------------------------------------------------------------

print("\nOUTPUTS")
print("-" * 70)
print("06_state_renewable_scale_ranking.csv")
print("06_jan_nov_2024_2025_generation_scale_change.csv")
print("06_annual_state_generation_scale.csv")
print("Charts saved in outputs/charts/")

print("\nA2.1 analysis completed successfully.")
