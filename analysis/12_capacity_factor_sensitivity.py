
from pathlib import Path
import pandas as pd

# =========================================================
# A4.2: CAPACITY FACTOR SENSITIVITY ANALYSIS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR / "outputs" /
    "10_monthly_state_source_capacity_factors.csv"
)

OUTPUT_FILE = (
    BASE_DIR / "outputs" /
    "12_capacity_factor_sensitivity.csv"
)

SOURCES = ["Solar", "Wind", "Hydro", "Bioenergy"]

print("=" * 75)
print("A4.2: CAPACITY FACTOR SENSITIVITY ANALYSIS")
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
    "Hours_in_Month",
    "Generation_GWh",
    "Capacity_MW",
    "Capacity_Factor_Pct",
    "Zero_Capacity_Positive_Generation",
    "Capacity_Factor_Above_100",
    "Source"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}\n"
        f"Available columns: {df.columns.tolist()}"
    )

print("\nINPUT VALIDATION")
print("-" * 75)
print("Rows:", len(df))
print("Sources:", df["Source"].nunique())
print("States / UTs:", df["State"].nunique())

unexpected_sources = set(df["Source"].dropna()) - set(SOURCES)

if unexpected_sources:
    print("Additional sources found:", unexpected_sources)

# ---------------------------------------------------------
# 2. CALCULATE ORIGINAL AND ADJUSTED FACTORS
# ---------------------------------------------------------

results = []

for source in SOURCES:

    part = df[df["Source"] == source].copy()

    generation = part["Generation_GWh"]
    capacity = part["Capacity_MW"]
    hours = part["Hours_in_Month"]

    # Valid observations for the original calculation
    valid = (
        generation.notna()
        & capacity.notna()
        & hours.notna()
        & (generation >= 0)
        & (capacity > 0)
        & (hours > 0)
    )

    # Observations exceeding 100%
    flagged = (
        part["Capacity_Factor_Above_100"]
        .fillna(False)
        .astype(bool)
    )

    # Zero capacity with positive generation
    zero_capacity_positive_generation = (
        capacity.eq(0) & generation.gt(0)
    )

    # Sensitivity subset: valid observations excluding >100%
    adjusted_valid = valid & ~flagged

    def calculate_capacity_factor(mask):

        total_generation = generation[mask].sum()

        total_capacity_hours = (
            capacity[mask] * hours[mask]
        ).sum()

        if total_capacity_hours <= 0:
            return float("nan")

        return (
            total_generation * 1000
            / total_capacity_hours
            * 100
        )

    original_factor = calculate_capacity_factor(valid)

    adjusted_factor = calculate_capacity_factor(adjusted_valid)

    results.append({

        "Source": source,

        "Total_State_Month_Rows": len(part),

        "Original_Valid_Months": int(valid.sum()),

        "Above_100_Months": int((valid & flagged).sum()),

        "Zero_Capacity_Positive_Generation_Months":
            int(zero_capacity_positive_generation.sum()),

        "Adjusted_Valid_Months": int(adjusted_valid.sum()),

        "Original_Weighted_Factor_Pct": original_factor,

        "Adjusted_Weighted_Factor_Pct": adjusted_factor,

        "Difference_Percentage_Points":
            adjusted_factor - original_factor

    })

# ---------------------------------------------------------
# 3. DISPLAY RESULTS
# ---------------------------------------------------------

result = pd.DataFrame(results)

print("\nCAPACITY FACTOR SENSITIVITY RESULTS")
print("-" * 75)

print(result.round(3).to_string(index=False))

# ---------------------------------------------------------
# 4. VALIDATE ORIGINAL RESULTS AGAINST SCRIPT 10
# ---------------------------------------------------------

expected_original = {
    "Solar": 17.465,
    "Wind": 21.283,
    "Hydro": 36.808,
    "Bioenergy": 14.885
}

print("\nORIGINAL RESULT RECONCILIATION")
print("-" * 75)

for _, row in result.iterrows():

    source = row["Source"]

    calculated = row["Original_Weighted_Factor_Pct"]

    expected = expected_original[source]

    difference = calculated - expected

    status = (
        "MATCH"
        if abs(difference) < 0.002
        else "CHECK"
    )

    print(
        f"{source:12s} "
        f"Calculated: {calculated:.3f}% | "
        f"Script 10: {expected:.3f}% | "
        f"Difference: {difference:.4f} pp | "
        f"{status}"
    )

# ---------------------------------------------------------
# 5. SAVE OUTPUT
# ---------------------------------------------------------

result.to_csv(OUTPUT_FILE, index=False)

print("\nOUTPUT")
print("-" * 75)
print("Saved:", OUTPUT_FILE.name)

print("\nSENSITIVITY ANALYSIS COMPLETED")
print("=" * 75)
