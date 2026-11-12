
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "outputs" / "10_monthly_state_source_capacity_factors.csv"

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("A4.2: CAPACITY FACTOR ANOMALY INVESTIGATION")
print("=" * 70)

# ---------------------------------------------------------
# 1. ALL ABOVE-100% OBSERVATIONS
# ---------------------------------------------------------

flagged = df[df["Capacity_Factor_Above_100"] == True].copy()

print("\nABOVE-100% OBSERVATIONS BY SOURCE AND STATE")
print("-" * 70)

summary = (
    flagged.groupby(["Source", "State"])
    .agg(
        Flagged_Months=("Month", "count"),
        Average_Generation_GWh=("Generation_GWh", "mean"),
        Average_Capacity_MW=("Capacity_MW", "mean"),
        Average_Capacity_Factor=("Capacity_Factor_Pct", "mean"),
        Maximum_Capacity_Factor=("Capacity_Factor_Pct", "max")
    )
    .reset_index()
    .sort_values(
        ["Source", "Flagged_Months"],
        ascending=[True, False]
    )
)

print(summary.round(3).to_string(index=False))

# ---------------------------------------------------------
# 2. KERALA BIOENERGY MONTHLY DETAILS
# ---------------------------------------------------------

print("\nKERALA BIOENERGY: ALL 53 MONTHS")
print("-" * 70)

kerala = df[
    (df["State"] == "Kerala") &
    (df["Source"] == "Bioenergy")
].copy()

print(
    kerala[[
        "Month",
        "Generation_GWh",
        "Capacity_MW",
        "Hours_in_Month",
        "Capacity_Factor_Pct",
        "Capacity_Factor_Above_100"
    ]].round(3).to_string(index=False)
)

print("\nKERALA BIOENERGY SUMMARY")
print("-" * 70)

print("Months:", len(kerala))
print("Positive generation months:", (kerala["Generation_GWh"] > 0).sum())
print("Zero generation months:", (kerala["Generation_GWh"] == 0).sum())
print("Unique capacity values:",
      sorted(kerala["Capacity_MW"].dropna().unique().tolist()))
print("Minimum capacity:", kerala["Capacity_MW"].min())
print("Maximum capacity:", kerala["Capacity_MW"].max())
print("Total generation:", kerala["Generation_GWh"].sum())
print("Above-100% months:",
      kerala["Capacity_Factor_Above_100"].sum())

# ---------------------------------------------------------
# 3. ABOVE-100% OBSERVATIONS FOR OTHER SOURCES
# ---------------------------------------------------------

print("\nOTHER ABOVE-100% OBSERVATIONS")
print("-" * 70)

other_flags = flagged[
    ~(
        (flagged["State"] == "Kerala") &
        (flagged["Source"] == "Bioenergy")
    )
]

if len(other_flags):
    print(
        other_flags[[
            "State",
            "Source",
            "Month",
            "Generation_GWh",
            "Capacity_MW",
            "Capacity_Factor_Pct"
        ]].round(3).to_string(index=False)
    )
else:
    print("No other above-100% observations.")

# ---------------------------------------------------------
# 4. ZERO CAPACITY WITH POSITIVE GENERATION
# ---------------------------------------------------------

print("\nZERO CAPACITY WITH POSITIVE GENERATION")
print("-" * 70)

zero_capacity = df[
    df["Zero_Capacity_Positive_Generation"] == True
]

if len(zero_capacity):
    print(
        zero_capacity[[
            "State",
            "Source",
            "Month",
            "Generation_GWh",
            "Capacity_MW"
        ]].to_string(index=False)
    )
else:
    print("No such observations.")

# ---------------------------------------------------------
# 5. SAVE DIAGNOSTIC OUTPUT
# ---------------------------------------------------------

summary.to_csv(
    BASE_DIR / "outputs" / "11_capacity_factor_anomaly_summary.csv",
    index=False
)

flagged.to_csv(
    BASE_DIR / "outputs" / "11_capacity_factor_flagged_records.csv",
    index=False
)

print("\nSaved diagnostic outputs.")
print("A4.2 ANOMALY INVESTIGATION COMPLETED")
