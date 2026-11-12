
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

GENERATION_FILE = OUTPUT_DIR / "state_month_analysis.csv"
CAPACITY_FILE = OUTPUT_DIR / "09_monthly_state_capacity.csv"

SOURCES = ["Solar", "Wind", "Hydro", "Bioenergy"]

print("=" * 70)
print("A4.2: STATE-LEVEL CAPACITY FACTOR ANALYSIS")
print("=" * 70)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

generation = pd.read_csv(GENERATION_FILE)
capacity = pd.read_csv(CAPACITY_FILE)

key = ["State", "Month"]

if generation.duplicated(key).any():
    raise ValueError("Duplicate state-month generation records.")

if capacity.duplicated(key).any():
    raise ValueError("Duplicate state-month capacity records.")

df = generation[
    key + SOURCES + ["Renewables", "Total Generation"]
].merge(
    capacity[key + SOURCES],
    on=key,
    how="left",
    suffixes=("_Generation_GWh", "_Capacity_MW"),
    validate="one_to_one"
)

# ---------------------------------------------------------
# 2. CALCULATE HOURS IN EACH MONTH
# ---------------------------------------------------------

df["Month_Period"] = pd.PeriodIndex(df["Month"], freq="M")

df["Hours_in_Month"] = (
    df["Month_Period"].dt.days_in_month * 24
)

# ---------------------------------------------------------
# 3. CALCULATE MONTHLY CAPACITY FACTORS
# ---------------------------------------------------------

for source in SOURCES:

    gen_col = f"{source}_Generation_GWh"
    cap_col = f"{source}_Capacity_MW"
    cf_col = f"{source}_Capacity_Factor_Pct"

    df[cf_col] = np.nan

    valid = (
        df[gen_col].notna() &
        df[cap_col].notna() &
        (df[cap_col] > 0)
    )

    df.loc[valid, cf_col] = (
        df.loc[valid, gen_col] * 1000 /
        (
            df.loc[valid, cap_col] *
            df.loc[valid, "Hours_in_Month"]
        ) * 100
    )

    df[f"{source}_Zero_Capacity_Positive_Generation"] = (
        df[cap_col].eq(0) & df[gen_col].gt(0)
    )

    df[f"{source}_Capacity_Factor_Above_100"] = (
        df[cf_col] > 100
    )

# ---------------------------------------------------------
# 4. PERIOD-LEVEL STATE SUMMARY
# ---------------------------------------------------------

state_rows = []

for (state, source), group in [
    ((state, source), group)
    for (state, source), group in
    pd.concat(
        [
            df[[
                "State", "Month",
                f"{source}_Generation_GWh",
                f"{source}_Capacity_MW",
                f"{source}_Capacity_Factor_Pct",
                "Hours_in_Month",
                f"{source}_Zero_Capacity_Positive_Generation",
                f"{source}_Capacity_Factor_Above_100"
            ]].rename(columns={
                f"{source}_Generation_GWh": "Generation_GWh",
                f"{source}_Capacity_MW": "Capacity_MW",
                f"{source}_Capacity_Factor_Pct": "Capacity_Factor_Pct",
                f"{source}_Zero_Capacity_Positive_Generation": "Zero_Capacity_Positive_Generation",
                f"{source}_Capacity_Factor_Above_100": "Above_100_Flag"
            }).assign(Source=source)
            for source in SOURCES
        ],
        ignore_index=True
    ).groupby(["State", "Source"])
]:

    valid = group[
        group["Generation_GWh"].notna() &
        group["Capacity_MW"].notna() &
        (group["Capacity_MW"] > 0)
    ]

    capacity_hours = (
        valid["Capacity_MW"] * valid["Hours_in_Month"]
    ).sum()

    generation_mwh = (
        valid["Generation_GWh"].sum() * 1000
    )

    weighted_cf = (
        generation_mwh / capacity_hours * 100
        if capacity_hours > 0 else np.nan
    )

    monthly_cf = valid["Capacity_Factor_Pct"].dropna()

    state_rows.append({
        "State": state,
        "Source": source,
        "Expected_Months": len(group),
        "Valid_Capacity_Months": len(valid),
        "Missing_Capacity_Months": group["Capacity_MW"].isna().sum(),
        "Zero_Capacity_Positive_Generation_Months":
            group["Zero_Capacity_Positive_Generation"].sum(),
        "Capacity_Factor_Above_100_Months":
            group["Above_100_Flag"].sum(),
        "Period_Generation_GWh": valid["Generation_GWh"].sum(),
        "Average_Capacity_MW": valid["Capacity_MW"].mean(),
        "Capacity_Weighted_Factor_Pct": weighted_cf,
        "Mean_Monthly_Factor_Pct": monthly_cf.mean(),
        "Median_Monthly_Factor_Pct": monthly_cf.median()
    })

state_summary = pd.DataFrame(state_rows)

# ---------------------------------------------------------
# 5. SOURCE-LEVEL NATIONAL SUMMARY
# ---------------------------------------------------------

national_rows = []

for source in SOURCES:

    gen_col = f"{source}_Generation_GWh"
    cap_col = f"{source}_Capacity_MW"
    cf_col = f"{source}_Capacity_Factor_Pct"

    valid = df[
        df[gen_col].notna() &
        df[cap_col].notna() &
        (df[cap_col] > 0)
    ]

    capacity_hours = (
        valid[cap_col] * valid["Hours_in_Month"]
    ).sum()

    generation_mwh = valid[gen_col].sum() * 1000

    national_rows.append({
        "Source": source,
        "Valid_State_Months": len(valid),
        "Missing_Capacity_Months": df[cap_col].isna().sum(),
        "Zero_Capacity_Positive_Generation_Months":
            df[f"{source}_Zero_Capacity_Positive_Generation"].sum(),
        "Capacity_Factor_Above_100_Months":
            df[f"{source}_Capacity_Factor_Above_100"].sum(),
        "Generation_GWh": valid[gen_col].sum(),
        "Capacity_Weighted_Factor_Pct": (
            generation_mwh / capacity_hours * 100
            if capacity_hours > 0 else np.nan
        ),
        "Mean_Monthly_Factor_Pct":
            valid[cf_col].mean(),
        "Median_Monthly_Factor_Pct":
            valid[cf_col].median()
    })

national_summary = pd.DataFrame(national_rows)

# ---------------------------------------------------------
# 6. MONTHLY STATE-SOURCE OUTPUT
# ---------------------------------------------------------

monthly_parts = []

for source in SOURCES:

    part = df[[
        "State",
        "Month",
        "Hours_in_Month",
        f"{source}_Generation_GWh",
        f"{source}_Capacity_MW",
        f"{source}_Capacity_Factor_Pct",
        f"{source}_Zero_Capacity_Positive_Generation",
        f"{source}_Capacity_Factor_Above_100"
    ]].copy()

    part.columns = [
        "State",
        "Month",
        "Hours_in_Month",
        "Generation_GWh",
        "Capacity_MW",
        "Capacity_Factor_Pct",
        "Zero_Capacity_Positive_Generation",
        "Capacity_Factor_Above_100"
    ]

    part["Source"] = source
    monthly_parts.append(part)

monthly_source = pd.concat(
    monthly_parts,
    ignore_index=True
)

# ---------------------------------------------------------
# 7. PRINT VALIDATION AND RESULTS
# ---------------------------------------------------------

print("\nINPUT VALIDATION")
print("-" * 70)
print("State-month rows:", len(df))
print("States / UTs:", df["State"].nunique())
print("Months:", df["Month"].nunique())
print("Period:", df["Month"].min(), "to", df["Month"].max())

print("\nCAPACITY FACTOR SUMMARY BY SOURCE")
print("-" * 70)
print(national_summary.round(3).to_string(index=False))

print("\nTOP 10 STATES BY CAPACITY-WEIGHTED FACTOR")
print("-" * 70)

for source in SOURCES:

    subset = state_summary[
        (state_summary["Source"] == source) &
        (state_summary["Valid_Capacity_Months"] >= 48)
    ].sort_values(
        "Capacity_Weighted_Factor_Pct",
        ascending=False
    )

    print(f"\n{source.upper()}")
    print(
        subset[[
            "State",
            "Period_Generation_GWh",
            "Average_Capacity_MW",
            "Capacity_Weighted_Factor_Pct",
            "Valid_Capacity_Months",
            "Capacity_Factor_Above_100_Months"
        ]].head(10).round(2).to_string(index=False)
    )

print("\nCAPACITY FACTOR ABOVE 100%")
print("-" * 70)

for source in SOURCES:
    count = df[
        f"{source}_Capacity_Factor_Above_100"
    ].sum()

    print(f"{source}: {count}")

# ---------------------------------------------------------
# 8. SAVE OUTPUTS
# ---------------------------------------------------------

monthly_source.to_csv(
    OUTPUT_DIR / "10_monthly_state_source_capacity_factors.csv",
    index=False
)

state_summary.to_csv(
    OUTPUT_DIR / "10_state_source_capacity_factor_summary.csv",
    index=False
)

national_summary.to_csv(
    OUTPUT_DIR / "10_national_source_capacity_factor_summary.csv",
    index=False
)

print("\nOUTPUTS")
print("-" * 70)
print("10_monthly_state_source_capacity_factors.csv")
print("10_state_source_capacity_factor_summary.csv")
print("10_national_source_capacity_factor_summary.csv")

print("\nA4.2 COMPLETED")
