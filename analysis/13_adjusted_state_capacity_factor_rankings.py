
from pathlib import Path
import pandas as pd

# =========================================================
# A4.2: ADJUSTED STATE-LEVEL CAPACITY FACTOR RANKINGS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR / "outputs" /
    "10_monthly_state_source_capacity_factors.csv"
)

RANKING_OUTPUT = (
    BASE_DIR / "outputs" /
    "13_adjusted_state_capacity_factor_rankings.csv"
)

EXCLUSION_OUTPUT = (
    BASE_DIR / "outputs" /
    "13_capacity_factor_exclusion_register.csv"
)

SOURCES = ["Solar", "Wind", "Hydro", "Bioenergy"]
MIN_VALID_MONTHS = 48

print("=" * 75)
print("A4.2: ADJUSTED STATE-LEVEL CAPACITY FACTOR RANKINGS")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD AND VALIDATE INPUT
# ---------------------------------------------------------

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

required_columns = [
    "State",
    "Month",
    "Source",
    "Generation_GWh",
    "Capacity_MW",
    "Hours_in_Month",
    "Capacity_Factor_Pct",
    "Capacity_Factor_Above_100",
    "Zero_Capacity_Positive_Generation"
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(
        f"Missing columns: {missing}\n"
        f"Available columns: {df.columns.tolist()}"
    )

df = df[df["Source"].isin(SOURCES)].copy()

if df.duplicated(["State", "Month", "Source"]).any():
    raise ValueError("Duplicate State-Month-Source records found.")

print("\nINPUT VALIDATION")
print("-" * 75)
print("Rows:", len(df))
print("States / UTs:", df["State"].nunique())
print("Months:", df["Month"].nunique())
print("Sources:", sorted(df["Source"].unique()))

# ---------------------------------------------------------
# 2. DEFINE VALID OBSERVATIONS AND EXCLUSIONS
# ---------------------------------------------------------

df["Above_100_Flag"] = (
    df["Capacity_Factor_Above_100"]
    .fillna(False)
    .astype(bool)
)

df["Zero_Capacity_Positive_Generation_Flag"] = (
    df["Zero_Capacity_Positive_Generation"]
    .fillna(False)
    .astype(bool)
)

df["Base_Valid"] = (
    df["Generation_GWh"].notna()
    & df["Capacity_MW"].notna()
    & df["Hours_in_Month"].notna()
    & (df["Generation_GWh"] >= 0)
    & (df["Capacity_MW"] > 0)
    & (df["Hours_in_Month"] > 0)
)

# Exclude above-100% observations from all source comparisons.
df["Exclude_Above_100"] = (
    df["Base_Valid"] & df["Above_100_Flag"]
)

# Kerala Bioenergy is excluded as a complete series from
# state-level comparison because its reported capacity
# remains fixed at 2.5 MW and its generation repeatedly
# implies capacity factors above 100%.
df["Exclude_Kerala_Bioenergy"] = (
    (df["Source"] == "Bioenergy")
    & (df["State"] == "Kerala")
)

df["Adjusted_Valid"] = (
    df["Base_Valid"]
    & ~df["Exclude_Above_100"]
    & ~df["Exclude_Kerala_Bioenergy"]
)

# ---------------------------------------------------------
# 3. CREATE EXCLUSION REGISTER
# ---------------------------------------------------------

exclusion_rows = []

for _, row in df.iterrows():

    reasons = []

    if row["Exclude_Above_100"]:
        reasons.append("Capacity factor above 100%")

    if row["Exclude_Kerala_Bioenergy"]:
        reasons.append(
            "Entire Kerala Bioenergy series excluded "
            "from state comparisons"
        )

    if row["Zero_Capacity_Positive_Generation_Flag"]:
        reasons.append(
            "Zero reported capacity with positive generation"
        )

    if reasons:
        exclusion_rows.append({
            "State": row["State"],
            "Month": row["Month"],
            "Source": row["Source"],
            "Generation_GWh": row["Generation_GWh"],
            "Capacity_MW": row["Capacity_MW"],
            "Original_Capacity_Factor_Pct":
                row["Capacity_Factor_Pct"],
            "Exclusion_Reason": "; ".join(reasons)
        })

exclusion_register = pd.DataFrame(exclusion_rows)

# ---------------------------------------------------------
# 4. CALCULATE STATE-LEVEL ADJUSTED FACTORS
# ---------------------------------------------------------

summary_rows = []

for (state, source), group in df.groupby(
    ["State", "Source"]
):

    valid = group[group["Adjusted_Valid"]].copy()

    total_generation = valid["Generation_GWh"].sum()

    total_capacity_hours = (
        valid["Capacity_MW"] *
        valid["Hours_in_Month"]
    ).sum()

    if total_capacity_hours > 0:

        weighted_factor = (
            total_generation * 1000
            / total_capacity_hours
            * 100
        )

        monthly_factors = (
            valid["Generation_GWh"] * 1000
            / (
                valid["Capacity_MW"] *
                valid["Hours_in_Month"]
            )
            * 100
        )

        mean_monthly_factor = monthly_factors.mean()
        median_monthly_factor = monthly_factors.median()

    else:
        weighted_factor = float("nan")
        mean_monthly_factor = float("nan")
        median_monthly_factor = float("nan")

    valid_months = len(valid)

    eligible = valid_months >= MIN_VALID_MONTHS

    summary_rows.append({

        "State": state,
        "Source": source,

        "Original_Valid_Months":
            int(group["Base_Valid"].sum()),

        "Excluded_Above_100_Months":
            int(group["Exclude_Above_100"].sum()),

        "Excluded_Kerala_Bioenergy_Months":
            int(group["Exclude_Kerala_Bioenergy"].sum()),

        "Zero_Capacity_Positive_Generation_Months":
            int(group["Zero_Capacity_Positive_Generation_Flag"].sum()),

        "Adjusted_Valid_Months": valid_months,

        "Adjusted_Generation_GWh": total_generation,

        "Average_Capacity_MW":
            valid["Capacity_MW"].mean()
            if valid_months > 0 else float("nan"),

        "Adjusted_Weighted_Factor_Pct": weighted_factor,

        "Mean_Monthly_Factor_Pct": mean_monthly_factor,

        "Median_Monthly_Factor_Pct": median_monthly_factor,

        "Ranking_Eligible": eligible

    })

summary = pd.DataFrame(summary_rows)

# ---------------------------------------------------------
# 5. ASSIGN RANKS ONLY TO ELIGIBLE STATES
# ---------------------------------------------------------

summary["Rank"] = pd.Series(
    pd.NA, index=summary.index, dtype="Int64"
)

for source in SOURCES:

    mask = (
        (summary["Source"] == source)
        & summary["Ranking_Eligible"]
        & summary["Adjusted_Weighted_Factor_Pct"].notna()
    )

    summary.loc[mask, "Rank"] = (
        summary.loc[mask, "Adjusted_Weighted_Factor_Pct"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

summary["Ranking_Status"] = summary["Ranking_Eligible"].map({
    True: "Eligible",
    False: "Insufficient valid months"
})

summary = summary.sort_values(
    ["Source", "Rank", "State"],
    na_position="last"
).reset_index(drop=True)

# ---------------------------------------------------------
# 6. DISPLAY VALIDATION AND RANKINGS
# ---------------------------------------------------------

print("\nEXCLUSION SUMMARY")
print("-" * 75)

for source in SOURCES:

    part = df[df["Source"] == source]

    print(
        f"{source:12s} | "
        f">100% exclusions: "
        f"{int(part['Exclude_Above_100'].sum()):3d} | "
        f"Kerala series exclusions: "
        f"{int(part['Exclude_Kerala_Bioenergy'].sum()):3d} | "
        f"Zero-capacity positive-generation: "
        f"{int(part['Zero_Capacity_Positive_Generation_Flag'].sum()):3d}"
    )

print("\nADJUSTED STATE-LEVEL RANKINGS")
print("-" * 75)

for source in SOURCES:

    print(f"\n{source.upper()}")
    print("-" * 75)

    display = summary[
        (summary["Source"] == source)
        & summary["Ranking_Eligible"]
    ].sort_values("Rank")

    if display.empty:
        print("No states meet the valid-month threshold.")
        continue

    print(
        display[[
            "Rank",
            "State",
            "Adjusted_Weighted_Factor_Pct",
            "Adjusted_Valid_Months",
            "Adjusted_Generation_GWh",
            "Average_Capacity_MW"
        ]].round(3).to_string(index=False)
    )

print("\nSTATES NOT ELIGIBLE FOR RANKING")
print("-" * 75)

ineligible = summary[~summary["Ranking_Eligible"]]

if ineligible.empty:
    print("All state-source combinations meet the threshold.")
else:
    print(
        ineligible[[
            "State",
            "Source",
            "Adjusted_Valid_Months",
            "Ranking_Status"
        ]].to_string(index=False)
    )

# ---------------------------------------------------------
# 7. SAVE OUTPUTS
# ---------------------------------------------------------

summary.to_csv(RANKING_OUTPUT, index=False)

exclusion_register.to_csv(
    EXCLUSION_OUTPUT,
    index=False
)

print("\nOUTPUTS")
print("-" * 75)
print(RANKING_OUTPUT.name)
print(EXCLUSION_OUTPUT.name)

print("\nA4.2 ADJUSTED STATE RANKINGS COMPLETED")
print("=" * 75)
