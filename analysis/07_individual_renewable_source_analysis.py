
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# A3: INDIVIDUAL RENEWABLE-SOURCE ANALYSIS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"

STATE_FILE = OUTPUT_DIR / "state_month_analysis.csv"
NATIONAL_FILE = OUTPUT_DIR / "national_month_analysis.csv"

SOURCES = [
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other Renewables"
]

RENEWABLE_COL = "Renewables"
TOTAL_COL = "Total Generation"

STATE_START = "2021-07"
STATE_END = "2025-11"

NATIONAL_START = "2019-01"
NATIONAL_END = "2025-11"

TOLERANCE = 1e-6


print("=" * 70)
print("A3: INDIVIDUAL RENEWABLE-SOURCE ANALYSIS")
print("=" * 70)


# ------------------------------------------------------------
# 1. LOAD AND VALIDATE INPUTS
# ------------------------------------------------------------

for path in [STATE_FILE, NATIONAL_FILE]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

states = pd.read_csv(STATE_FILE)
national = pd.read_csv(NATIONAL_FILE)

required = {
    "State",
    "Month",
    RENEWABLE_COL,
    TOTAL_COL,
    *SOURCES
}

for label, df in [
    ("State", states),
    ("National", national)
]:
    missing_columns = required - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{label} dataset is missing columns: {missing_columns}"
        )

    df["Month"] = df["Month"].astype(str)

    for col in [RENEWABLE_COL, TOTAL_COL] + SOURCES:
        df[col] = pd.to_numeric(df[col], errors="coerce")


states = states[
    states["Month"].between(STATE_START, STATE_END)
].copy()

national = national[
    (national["State"] == "India Total")
    & national["Month"].between(NATIONAL_START, NATIONAL_END)
].copy()


state_duplicates = states.duplicated(
    subset=["State", "Month"]
).sum()

national_duplicates = national.duplicated(
    subset=["Month"]
).sum()

state_missing = states[
    [RENEWABLE_COL, TOTAL_COL] + SOURCES
].isna().any(axis=1).sum()

national_missing = national[
    [RENEWABLE_COL, TOTAL_COL] + SOURCES
].isna().any(axis=1).sum()

if state_duplicates or national_duplicates:
    raise ValueError(
        f"Duplicates found: state={state_duplicates}, "
        f"national={national_duplicates}"
    )

if state_missing or national_missing:
    raise ValueError(
        f"Missing required values: state={state_missing}, "
        f"national={national_missing}"
    )

if (
    states[[RENEWABLE_COL, TOTAL_COL] + SOURCES] < 0
).any().any():
    raise ValueError("Negative state generation values detected.")

if (
    national[[RENEWABLE_COL, TOTAL_COL] + SOURCES] < 0
).any().any():
    raise ValueError("Negative national generation values detected.")

if (states[RENEWABLE_COL] <= 0).any():
    raise ValueError("Non-positive state renewable generation detected.")

if (national[RENEWABLE_COL] <= 0).any():
    raise ValueError("Non-positive national renewable generation detected.")

if (states[TOTAL_COL] <= 0).any():
    raise ValueError("Non-positive state total generation detected.")

if (national[TOTAL_COL] <= 0).any():
    raise ValueError("Non-positive national total generation detected.")


print("\nINPUT VALIDATION")
print("-" * 70)
print(f"State-month rows: {len(states):,}")
print(f"States / UTs: {states['State'].nunique()}")
print(f"State period: {states['Month'].min()} to {states['Month'].max()}")
print(f"National months: {len(national)}")
print(
    f"National period: {national['Month'].min()} "
    f"to {national['Month'].max()}"
)
print(f"State duplicate records: {state_duplicates}")
print(f"National duplicate records: {national_duplicates}")
print(f"State rows with missing required values: {state_missing}")
print(f"National rows with missing required values: {national_missing}")


# ------------------------------------------------------------
# 2. SOURCE RECONCILIATION
# ------------------------------------------------------------

states["Source_Sum_GWh"] = states[SOURCES].sum(axis=1)
national["Source_Sum_GWh"] = national[SOURCES].sum(axis=1)

states["Source_Reconciliation_Difference_GWh"] = (
    states["Source_Sum_GWh"] - states[RENEWABLE_COL]
)

national["Source_Reconciliation_Difference_GWh"] = (
    national["Source_Sum_GWh"] - national[RENEWABLE_COL]
)

state_mismatch = (
    states["Source_Reconciliation_Difference_GWh"].abs()
    > TOLERANCE
).sum()

national_mismatch = (
    national["Source_Reconciliation_Difference_GWh"].abs()
    > TOLERANCE
).sum()

state_max_difference = (
    states["Source_Reconciliation_Difference_GWh"].abs().max()
)

national_max_difference = (
    national["Source_Reconciliation_Difference_GWh"].abs().max()
)

print("\nRENEWABLE SOURCE RECONCILIATION")
print("-" * 70)
print(f"State-months outside tolerance: {state_mismatch}")
print(f"Maximum state absolute difference: {state_max_difference:.10f} GWh")
print(f"National months outside tolerance: {national_mismatch}")
print(
    "Maximum national absolute difference: "
    f"{national_max_difference:.10f} GWh"
)


# ------------------------------------------------------------
# 3. NATIONAL MONTHLY SOURCE METRICS
# ------------------------------------------------------------

national_monthly = national[
    ["Month", RENEWABLE_COL, TOTAL_COL] + SOURCES
].copy()

for source in SOURCES:
    national_monthly[f"{source}_Share_of_Renewables_Pct"] = (
        national_monthly[source]
        / national_monthly[RENEWABLE_COL]
        * 100
    )

    national_monthly[f"{source}_Share_of_Total_Generation_Pct"] = (
        national_monthly[source]
        / national_monthly[TOTAL_COL]
        * 100
    )

national_monthly.to_csv(
    OUTPUT_DIR / "07_national_monthly_source_metrics.csv",
    index=False
)


# ------------------------------------------------------------
# 4. NATIONAL ANNUAL SOURCE SUMMARY
# ------------------------------------------------------------

national_annual = national_monthly.copy()
national_annual["Year"] = national_annual["Month"].str[:4]

annual_agg = (
    national_annual.groupby("Year", as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum"),
        **{
            f"{source}_GWh": (source, "sum")
            for source in SOURCES
        }
    )
)

for source in SOURCES:
    annual_agg[f"{source}_Share_of_Renewables_Pct"] = (
        annual_agg[f"{source}_GWh"]
        / annual_agg["Renewable_Generation_GWh"]
        * 100
    )

    annual_agg[f"{source}_Share_of_Total_Generation_Pct"] = (
        annual_agg[f"{source}_GWh"]
        / annual_agg["Total_Generation_GWh"]
        * 100
    )

annual_agg["Period_Status"] = annual_agg["Months_Observed"].apply(
    lambda n: (
        "Complete calendar year"
        if n == 12
        else "Partial year"
    )
)

annual_agg.to_csv(
    OUTPUT_DIR / "07_national_annual_source_summary.csv",
    index=False
)

print("\nNATIONAL ANNUAL SOURCE TRENDS")
print("-" * 70)

display_columns = [
    "Year",
    "Months_Observed",
    "Solar_GWh",
    "Wind_GWh",
    "Hydro_GWh",
    "Bioenergy_GWh",
    "Other Renewables_GWh",
    "Period_Status"
]

print(
    annual_agg[display_columns]
    .round(2)
    .to_string(index=False)
)


# ------------------------------------------------------------
# 5. NATIONAL SOURCE COMPOSITION OVER FULL PERIOD
# ------------------------------------------------------------

national_source_totals = pd.DataFrame({
    "Source": SOURCES,
    "Generation_GWh": [
        national[source].sum() for source in SOURCES
    ]
})

national_source_totals["Share_of_Renewables_Pct"] = (
    national_source_totals["Generation_GWh"]
    / national[RENEWABLE_COL].sum()
    * 100
)

national_source_totals = national_source_totals.sort_values(
    "Generation_GWh", ascending=False
)

national_source_totals.to_csv(
    OUTPUT_DIR / "07_national_source_composition.csv",
    index=False
)

print("\nNATIONAL SOURCE COMPOSITION")
print("-" * 70)
print(
    national_source_totals.round(2).to_string(index=False)
)


# ------------------------------------------------------------
# 6. STATE-LEVEL SOURCE METRICS
# ------------------------------------------------------------

state_totals = (
    states.groupby("State", as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum"),
        **{
            f"{source}_GWh": (source, "sum")
            for source in SOURCES
        }
    )
)

# National source totals over the same common state period.
national_common = national[
    national["Month"].between(STATE_START, STATE_END)
].copy()

national_source_denominators = {
    source: national_common[source].sum()
    for source in SOURCES
}

national_renewable_denominator = national_common[RENEWABLE_COL].sum()

records = []

for _, row in state_totals.iterrows():
    state = row["State"]

    for source in SOURCES:
        source_gwh = row[f"{source}_GWh"]

        records.append({
            "State": state,
            "Source": source,
            "Months_Observed": row["Months_Observed"],
            "Source_Generation_GWh": source_gwh,
            "Renewable_Generation_GWh": row["Renewable_Generation_GWh"],
            "Total_Generation_GWh": row["Total_Generation_GWh"],
            "Source_Share_of_Renewables_Pct": (
                source_gwh / row["Renewable_Generation_GWh"] * 100
            ),
            "Source_Share_of_Total_Generation_Pct": (
                source_gwh / row["Total_Generation_GWh"] * 100
            ),
            "Contribution_to_India_Source_Pct": (
                source_gwh / national_source_denominators[source] * 100
            )
        })

state_source = pd.DataFrame(records)

state_source.to_csv(
    OUTPUT_DIR / "07_state_source_period_metrics.csv",
    index=False
)


# ------------------------------------------------------------
# 7. STATE RANKINGS BY SOURCE
# ------------------------------------------------------------

ranking_records = []

for source in SOURCES:
    subset = state_source[
        state_source["Source"] == source
    ].copy()

    subset = subset.sort_values(
        "Source_Generation_GWh",
        ascending=False
    ).reset_index(drop=True)

    subset["Generation_Rank"] = range(1, len(subset) + 1)

    subset["Renewable_Mix_Share_Rank"] = (
        subset["Source_Share_of_Renewables_Pct"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    subset["National_Contribution_Rank"] = (
        subset["Contribution_to_India_Source_Pct"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    ranking_records.append(subset)

rankings = pd.concat(ranking_records, ignore_index=True)

rankings.to_csv(
    OUTPUT_DIR / "07_state_source_rankings.csv",
    index=False
)

print("\nTOP 5 STATES BY SOURCE GENERATION")
print("-" * 70)

for source in SOURCES:
    subset = rankings[
        rankings["Source"] == source
    ].head(5)

    print(f"\n{source.upper()}")
    print(
        subset[
            [
                "State",
                "Source_Generation_GWh",
                "Source_Share_of_Renewables_Pct",
                "Contribution_to_India_Source_Pct"
            ]
        ].round(2).to_string(index=False)
    )


# ------------------------------------------------------------
# 8. JAN-NOV 2024 VS JAN-NOV 2025
# ------------------------------------------------------------

recent = states[
    states["Month"].str.startswith(("2024-", "2025-"))
].copy()

recent = recent[
    recent["Month"].str[5:7].astype(int).between(1, 11)
].copy()

recent["Year"] = recent["Month"].str[:4]

recent_agg = (
    recent.groupby(["State", "Year"], as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum"),
        **{
            f"{source}_GWh": (source, "sum")
            for source in SOURCES
        }
    )
)

for source in SOURCES:
    recent_agg[f"{source}_Share_of_Renewables_Pct"] = (
        recent_agg[f"{source}_GWh"]
        / recent_agg["Renewable_Generation_GWh"]
        * 100
    )

recent_records = []

for source in SOURCES:
    source_wide = recent_agg.pivot(
        index="State",
        columns="Year",
        values=[
            f"{source}_GWh",
            f"{source}_Share_of_Renewables_Pct"
        ]
    )

    source_wide.columns = [
        f"{metric}_{year}" for metric, year in source_wide.columns
    ]

    source_wide = source_wide.reset_index()

    for metric in [
        f"{source}_GWh",
        f"{source}_Share_of_Renewables_Pct"
    ]:
        col24 = f"{metric}_2024"
        col25 = f"{metric}_2025"

        source_wide[f"{metric}_Change"] = (
            source_wide[col25] - source_wide[col24]
        )

        if metric.endswith("_GWh"):
            source_wide[f"{metric}_Change_Pct"] = (
                source_wide[f"{metric}_Change"]
                / source_wide[col24].replace(0, np.nan)
                * 100
            )

    source_wide["Source"] = source
    recent_records.append(source_wide)

recent_comparison = pd.concat(
    recent_records,
    ignore_index=True
)

recent_comparison.to_csv(
    OUTPUT_DIR / "07_state_source_change_2024_2025.csv",
    index=False
)

print("\nJAN-NOV 2024 VS JAN-NOV 2025")
print("-" * 70)

for source in SOURCES:
    subset = recent_comparison[
        recent_comparison["Source"] == source
    ].sort_values(
        f"{source}_GWh_Change",
        ascending=False
    )

    print(f"\n{source.upper()} — TOP 5 BY GENERATION INCREASE")
    print(
        subset[
            [
                "State",
                f"{source}_GWh_2024",
                f"{source}_GWh_2025",
                f"{source}_GWh_Change",
                f"{source}_GWh_Change_Pct"
            ]
        ].head(5).round(2).to_string(index=False)
    )


# ------------------------------------------------------------
# 9. ANNUAL STATE-SOURCE SUMMARY
# ------------------------------------------------------------

states_annual = states.copy()
states_annual["Year"] = states_annual["Month"].str[:4]

annual_state_source = (
    states_annual.groupby(["State", "Year"], as_index=False)
    .agg(
        Months_Observed=("Month", "nunique"),
        Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
        Total_Generation_GWh=(TOTAL_COL, "sum"),
        **{
            f"{source}_GWh": (source, "sum")
            for source in SOURCES
        }
    )
)

for source in SOURCES:
    annual_state_source[f"{source}_Share_of_Renewables_Pct"] = (
        annual_state_source[f"{source}_GWh"]
        / annual_state_source["Renewable_Generation_GWh"]
        * 100
    )

annual_state_source["Period_Status"] = (
    annual_state_source["Months_Observed"].apply(
        lambda n: (
            "Complete calendar year"
            if n == 12
            else "Partial year"
        )
    )
)

annual_state_source.to_csv(
    OUTPUT_DIR / "07_annual_state_source_summary.csv",
    index=False
)


# ------------------------------------------------------------
# 10. CHARTS
# ------------------------------------------------------------

CHART_DIR.mkdir(parents=True, exist_ok=True)

# Chart 1: National annual generation by source
plt.figure(figsize=(12, 7))

for source in SOURCES:
    plt.plot(
        national_annual["Year"],
        national_annual[source],
        marker="o",
        label=source
    )

plt.xlabel("Year")
plt.ylabel("Generation (GWh)")
plt.title("India: Annual Generation by Renewable Source")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(
    CHART_DIR / "07_national_annual_source_trends.png",
    dpi=200
)
plt.close()


# Chart 2: National annual renewable mix
plt.figure(figsize=(12, 7))

bottom = np.zeros(len(annual_agg))

for source in SOURCES:
    values = annual_agg[f"{source}_Share_of_Renewables_Pct"].values

    plt.bar(
        annual_agg["Year"],
        values,
        bottom=bottom,
        label=source
    )

    bottom += values

plt.xlabel("Year")
plt.ylabel("Share of renewable generation (%)")
plt.title("India: Renewable Generation Composition by Year")
plt.legend()
plt.tight_layout()
plt.savefig(
    CHART_DIR / "07_national_renewable_source_composition.png",
    dpi=200
)
plt.close()


# Chart 3: Top 10 states by generation for each source
for source in SOURCES:
    subset = rankings[
        rankings["Source"] == source
    ].nlargest(10, "Source_Generation_GWh")

    subset = subset.sort_values("Source_Generation_GWh")

    plt.figure(figsize=(10, 7))
    plt.barh(
        subset["State"],
        subset["Source_Generation_GWh"]
    )
    plt.xlabel("Generation (GWh)")
    plt.ylabel("State / UT")
    plt.title(
        f"Top 10 States / UTs by {source} Generation\n"
        "July 2021 – November 2025"
    )
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / f"07_top_states_{source.lower().replace(' ', '_')}.png",
        dpi=200
    )
    plt.close()


# ------------------------------------------------------------
# 11. FINAL OUTPUTS
# ------------------------------------------------------------

print("\nOUTPUTS")
print("-" * 70)
print("07_national_monthly_source_metrics.csv")
print("07_national_annual_source_summary.csv")
print("07_national_source_composition.csv")
print("07_state_source_period_metrics.csv")
print("07_state_source_rankings.csv")
print("07_state_source_change_2024_2025.csv")
print("07_annual_state_source_summary.csv")
print("Charts saved in outputs/charts/")

print("\nA3 analysis completed successfully.")
