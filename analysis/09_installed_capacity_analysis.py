
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

CAPACITY_FILE = BASE_DIR / "india_monthly.csv"
STATE_FILE = OUTPUT_DIR / "state_month_analysis.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

START_MONTH = "2021-07"
END_MONTH = "2025-11"

SOURCES = [
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy"
]

CAPACITY_VARIABLES = [
    "Renewables",
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other Renewables",
    "Fossil"
]

print("=" * 70)
print("A4.1: INSTALLED RENEWABLE CAPACITY ANALYSIS")
print("=" * 70)

# ---------------------------------------------------------
# 1. LOAD AND FILTER DATA
# ---------------------------------------------------------

raw = pd.read_csv(CAPACITY_FILE, low_memory=False)

capacity = raw[
    (raw["Category"] == "Capacity") &
    (raw["Unit"] == "MW") &
    (raw["Variable"].isin(CAPACITY_VARIABLES))
].copy()

capacity["Date"] = pd.to_datetime(
    capacity["Date"], errors="coerce"
)

capacity["Month"] = (
    capacity["Date"].dt.to_period("M").astype(str)
)

capacity["Value"] = pd.to_numeric(
    capacity["Value"], errors="coerce"
)

capacity = capacity[
    (capacity["Month"] >= START_MONTH) &
    (capacity["Month"] <= END_MONTH)
].copy()

# Use only the 36 State/UT units in the existing analysis panel.
state_panel = pd.read_csv(STATE_FILE)

states = sorted(state_panel["State"].unique())

capacity = capacity[
    capacity["State"].isin(states)
].copy()

print("\nINPUT VALIDATION")
print("-" * 70)
print("States / UTs:", len(states))
print("Capacity records:", len(capacity))
print("Period:", START_MONTH, "to", END_MONTH)

# ---------------------------------------------------------
# 2. CHECK DUPLICATES
# ---------------------------------------------------------

key = ["State", "Date", "Variable", "Unit"]

duplicates = capacity[
    capacity.duplicated(key, keep=False)
]

print("Duplicate records:", len(duplicates))

if len(duplicates) > 0:
    raise ValueError("Duplicate capacity records detected.")

# ---------------------------------------------------------
# 3. CREATE MONTHLY CAPACITY PANEL
# ---------------------------------------------------------

capacity_wide = capacity.pivot(
    index=["State", "Month"],
    columns="Variable",
    values="Value"
).reset_index()

capacity_wide.columns.name = None

# Full expected state-month panel.
months = sorted(state_panel["Month"].unique())

expected = pd.MultiIndex.from_product(
    [states, months],
    names=["State", "Month"]
).to_frame(index=False)

panel = expected.merge(
    capacity_wide,
    on=["State", "Month"],
    how="left"
)

print("\nMONTHLY PANEL")
print("-" * 70)
print("Expected state-month rows:", len(expected))
print("Actual panel rows:", len(panel))
print("Duplicate state-month rows:",
      panel.duplicated(["State", "Month"]).sum())

# ---------------------------------------------------------
# 4. CAPACITY AVAILABILITY
# ---------------------------------------------------------

for variable in CAPACITY_VARIABLES:
    if variable not in panel.columns:
        panel[variable] = np.nan

    panel[f"{variable}_available"] = (
        panel[variable].notna()
    )

print("\nCAPACITY COVERAGE")
print("-" * 70)

for variable in CAPACITY_VARIABLES:
    observed = panel[variable].notna().sum()
    missing = panel[variable].isna().sum()
    positive = (panel[variable] > 0).sum()

    print(
        f"{variable:25s} "
        f"Observed: {observed:4d} | "
        f"Missing: {missing:4d} | "
        f"Positive: {positive:4d}"
    )

# ---------------------------------------------------------
# 5. STATE-LEVEL PERIOD SUMMARY
# ---------------------------------------------------------

summary_rows = []

for state, group in panel.groupby("State"):

    row = {
        "State": state,
        "Months_Expected": len(group)
    }

    for variable in CAPACITY_VARIABLES:

        values = group[variable].dropna()

        row[f"{variable}_Observed_Months"] = len(values)

        row[f"{variable}_Average_MW"] = (
            values.mean() if len(values) else np.nan
        )

        row[f"{variable}_Latest_MW"] = (
            values.iloc[-1] if len(values) else np.nan
        )

        row[f"{variable}_Latest_Month"] = (
            group.loc[
                group[variable].notna(), "Month"
            ].iloc[-1]
            if group[variable].notna().any()
            else None
        )

    summary_rows.append(row)

state_summary = pd.DataFrame(summary_rows)

state_summary = state_summary.sort_values(
    "Renewables_Average_MW",
    ascending=False
)

# ---------------------------------------------------------
# 6. NATIONAL SOURCE CAPACITY PROFILE
# ---------------------------------------------------------

national_rows = []

for variable in CAPACITY_VARIABLES:

    values = panel[variable].dropna()

    national_rows.append({
        "Variable": variable,
        "State_Month_Observations": len(values),
        "Average_State_Capacity_MW": values.mean(),
        "Average_National_Capacity_MW": (
            panel.groupby("Month")[variable].sum(min_count=1).mean()
        ),
        "Latest_National_Capacity_MW": (
            panel.groupby("Month")[variable].sum(min_count=1).iloc[-1]
        )
    })

national_summary = pd.DataFrame(national_rows)

# ---------------------------------------------------------
# 7. CAPACITY COMPONENT RECONCILIATION
# ---------------------------------------------------------

component_columns = SOURCES

panel["Four_Source_Capacity_Sum_MW"] = (
    panel[component_columns].sum(
        axis=1,
        min_count=len(component_columns)
    )
)

comparable = panel[
    panel["Renewables"].notna() &
    panel["Four_Source_Capacity_Sum_MW"].notna()
].copy()

comparable["Difference_MW"] = (
    comparable["Four_Source_Capacity_Sum_MW"] -
    comparable["Renewables"]
)

print("\nRENEWABLE CAPACITY COMPONENT RECONCILIATION")
print("-" * 70)
print("Comparable state-months:", len(comparable))

if len(comparable):
    print(
        "Mean absolute difference:",
        comparable["Difference_MW"].abs().mean()
    )
    print(
        "Maximum absolute difference:",
        comparable["Difference_MW"].abs().max()
    )
    print(
        "Mean signed difference:",
        comparable["Difference_MW"].mean()
    )

# ---------------------------------------------------------
# 8. ANNUAL CAPACITY SUMMARY
# ---------------------------------------------------------

panel["Year"] = panel["Month"].str[:4]

annual_rows = []

for (state, year), group in panel.groupby(["State", "Year"]):

    row = {
        "State": state,
        "Year": year,
        "Months_Expected": len(group)
    }

    for variable in CAPACITY_VARIABLES:
        values = group[variable].dropna()

        row[f"{variable}_Average_MW"] = (
            values.mean() if len(values) else np.nan
        )

        row[f"{variable}_Observed_Months"] = len(values)

    annual_rows.append(row)

annual_summary = pd.DataFrame(annual_rows)

# ---------------------------------------------------------
# 9. SAVE OUTPUTS
# ---------------------------------------------------------

panel.to_csv(
    OUTPUT_DIR / "09_monthly_state_capacity.csv",
    index=False
)

state_summary.to_csv(
    OUTPUT_DIR / "09_state_period_capacity_summary.csv",
    index=False
)

national_summary.to_csv(
    OUTPUT_DIR / "09_national_capacity_summary.csv",
    index=False
)

comparable.to_csv(
    OUTPUT_DIR / "09_capacity_component_reconciliation.csv",
    index=False
)

annual_summary.to_csv(
    OUTPUT_DIR / "09_annual_state_capacity_summary.csv",
    index=False
)

# ---------------------------------------------------------
# 10. PRINT RESULTS
# ---------------------------------------------------------

print("\nTOP 10 STATES BY AVERAGE RENEWABLE CAPACITY")
print("-" * 70)

display_columns = [
    "State",
    "Renewables_Average_MW",
    "Renewables_Latest_MW",
    "Renewables_Observed_Months"
]

print(
    state_summary[display_columns]
    .head(10)
    .round(2)
    .to_string(index=False)
)

print("\nNATIONAL CAPACITY PROFILE")
print("-" * 70)
print(national_summary.round(2).to_string(index=False))

print("\nOUTPUTS")
print("-" * 70)

for filename in [
    "09_monthly_state_capacity.csv",
    "09_state_period_capacity_summary.csv",
    "09_national_capacity_summary.csv",
    "09_capacity_component_reconciliation.csv",
    "09_annual_state_capacity_summary.csv"
]:
    print(filename)

print("\nA4.1 COMPLETED")
