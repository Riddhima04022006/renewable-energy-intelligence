
"""
03_build_analysis_dataset.py

PURPOSE
-------
Prepare analysis-ready monthly electricity generation datasets
from the original Ember India dataset.

INPUT
-----
../india_monthly.csv

OUTPUTS
-------
outputs/state_month_analysis.csv
outputs/national_month_analysis.csv
outputs/others_month_analysis.csv
outputs/missing_record_register.csv
outputs/03_build_validation.txt

SCOPE
-----
1. State/UT comparison: July 2021 - November 2025
2. National analysis: January 2019 - November 2025
3. Others: separate reporting scope

METHODOLOGY
-----------
- Uses electricity generation records measured in GWh only.
- Retains all 16 generation variables.
- Does not modify the original dataset.
- Does not convert missing values to zero.
- Does not interpolate or forward-fill generation.
- Distinguishes missing records from blank values.
- Creates metric-specific availability flags.
"""

from pathlib import Path
import pandas as pd


# ==========================================================
# 1. PATHS AND CONFIGURATION
# ==========================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_DIR / "india_monthly.csv"

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATE_START = pd.Period("2021-07", freq="M")
STATE_END = pd.Period("2025-11", freq="M")

NATIONAL_START = pd.Period("2019-01", freq="M")
NATIONAL_END = pd.Period("2025-11", freq="M")

EXPECTED_VARIABLES = [
    "Bioenergy",
    "Clean",
    "Coal",
    "Fossil",
    "Gas",
    "Gas and Other Fossil",
    "Hydro",
    "Hydro, Bioenergy and Other Renewables",
    "Nuclear",
    "Other Fossil",
    "Other Renewables",
    "Renewables",
    "Solar",
    "Total Generation",
    "Wind",
    "Wind and Solar"
]

RENEWABLE_SOURCES = [
    "Solar",
    "Wind",
    "Hydro",
    "Bioenergy",
    "Other Renewables"
]

FOSSIL_SOURCES = [
    "Coal",
    "Gas",
    "Other Fossil"
]


# ==========================================================
# 2. LOAD ORIGINAL DATA
# ==========================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Original dataset not found: {INPUT_FILE}"
    )

df = pd.read_csv(
    INPUT_FILE,
    dtype=str,
    keep_default_na=False
)

required_columns = [
    "State",
    "State code",
    "State type",
    "Date",
    "Category",
    "Variable",
    "Unit",
    "Value"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Required columns missing: {missing_columns}"
    )


# ==========================================================
# 3. FILTER GENERATION DATA IN GWh
# ==========================================================

gen = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
].copy()

gen["Date"] = pd.to_datetime(
    gen["Date"],
    errors="coerce"
)

if gen["Date"].isna().any():
    raise ValueError(
        "Invalid dates found in GWh generation records."
    )

gen["Month"] = gen["Date"].dt.to_period("M")

gen["Numeric Value"] = pd.to_numeric(
    gen["Value"].str.strip(),
    errors="coerce"
)

actual_variables = set(gen["Variable"].unique())
expected_variables = set(EXPECTED_VARIABLES)

if actual_variables != expected_variables:
    raise ValueError(
        "Generation schema differs from the verified schema.\n"
        f"Unexpected variables: "
        f"{sorted(actual_variables - expected_variables)}\n"
        f"Missing variables: "
        f"{sorted(expected_variables - actual_variables)}"
    )

# Confirm uniqueness before pivoting.
duplicate_mask = gen.duplicated(
    subset=["State", "Date", "Variable", "Unit"],
    keep=False
)

if duplicate_mask.any():
    raise ValueError(
        f"Found {duplicate_mask.sum()} duplicate GWh records. "
        "Resolve them before building the analytical dataset."
    )


# ==========================================================
# 4. IDENTIFY REPORTING UNITS
# ==========================================================

SPECIAL_LABELS = ["India Total", "Others"]

state_labels = sorted(
    label for label in gen["State"].unique()
    if label not in SPECIAL_LABELS
)

if len(state_labels) != 36:
    raise ValueError(
        f"Expected 36 State/UT labels, found {len(state_labels)}. "
        "Review the reporting geography before proceeding."
    )

# State metadata must remain consistent.
metadata_counts = (
    gen.groupby("State")[["State code", "State type"]]
    .nunique()
)

if (metadata_counts > 1).any().any():
    raise ValueError(
        "State code or State type changes across records. "
        "Review metadata before building the panel."
    )

state_metadata = (
    gen[["State", "State code", "State type"]]
    .drop_duplicates()
)


# ==========================================================
# 5. FUNCTION TO BUILD A MONTHLY ANALYTICAL PANEL
# ==========================================================

def build_panel(records, labels, months, dataset_name):

    records = records[
        records["State"].isin(labels) &
        records["Month"].isin(months)
    ].copy()

    # Expected state-month combinations.
    full_index = pd.MultiIndex.from_product(
        [labels, months],
        names=["State", "Month"]
    )

    # Pivot numeric values.
    value_panel = records.pivot(
        index=["State", "Month"],
        columns="Variable",
        values="Numeric Value"
    )

    value_panel = value_panel.reindex(
        index=full_index,
        columns=EXPECTED_VARIABLES
    )

    # Independently track whether a source record exists.
    presence_panel = (
        records.assign(Record_Present=True)
        .pivot(
            index=["State", "Month"],
            columns="Variable",
            values="Record_Present"
        )
        .reindex(
            index=full_index,
            columns=EXPECTED_VARIABLES
        )
        .fillna(False)
        .astype(bool)
    )

    # Start with numeric values.
    panel = value_panel.copy()

    # Add record-presence and blank-value flags.
    for variable in EXPECTED_VARIABLES:

        present = presence_panel[variable]
        value = value_panel[variable]

        panel[f"record_present__{variable}"] = present
        panel[f"value_missing__{variable}"] = (
            present & value.isna()
        )
        panel[f"record_missing__{variable}"] = ~present

    # Metric-specific availability.
    panel["total_generation_available"] = (
        panel["Total Generation"].notna()
    )

    panel["renewable_generation_available"] = (
        panel["Renewables"].notna()
    )

    panel["fossil_generation_available"] = (
        panel["Fossil"].notna()
    )

    # Share calculations require both numerator and
    # a non-zero total-generation denominator.
    panel["renewable_share_inputs_available"] = (
        panel["Renewables"].notna() &
        panel["Total Generation"].notna() &
        (panel["Total Generation"] != 0)
    )

    panel["fossil_share_inputs_available"] = (
        panel["Fossil"].notna() &
        panel["Total Generation"].notna() &
        (panel["Total Generation"] != 0)
    )

    panel["renewable_source_breakdown_available"] = (
        panel[RENEWABLE_SOURCES].notna().all(axis=1)
    )

    panel["fossil_source_breakdown_available"] = (
        panel[FOSSIL_SOURCES].notna().all(axis=1)
    )

    panel = panel.reset_index()

    # Use a readable month representation.
    panel["Month"] = panel["Month"].astype(str)

    # Add geographic metadata to state-level output.
    if dataset_name == "state":
        panel = panel.merge(
            state_metadata,
            on="State",
            how="left",
            validate="many_to_one"
        )

    # Put identifying columns first.
    first_columns = ["State", "Month"]

    if dataset_name == "state":
        first_columns += ["State code", "State type"]

    remaining_columns = [
        col for col in panel.columns
        if col not in first_columns
    ]

    panel = panel[first_columns + remaining_columns]

    return panel


# ==========================================================
# 6. BUILD STATE/UT DATASET
# ==========================================================

state_months = pd.period_range(
    STATE_START,
    STATE_END,
    freq="M"
)

state_records = gen[
    gen["Month"].between(STATE_START, STATE_END)
]

state_panel = build_panel(
    records=state_records,
    labels=state_labels,
    months=state_months,
    dataset_name="state"
)

state_file = OUTPUT_DIR / "state_month_analysis.csv"

state_panel.to_csv(
    state_file,
    index=False
)


# ==========================================================
# 7. BUILD NATIONAL DATASET
# ==========================================================

national_months = pd.period_range(
    NATIONAL_START,
    NATIONAL_END,
    freq="M"
)

national_panel = build_panel(
    records=gen,
    labels=["India Total"],
    months=national_months,
    dataset_name="national"
)

national_file = OUTPUT_DIR / "national_month_analysis.csv"

national_panel.to_csv(
    national_file,
    index=False
)


# ==========================================================
# 8. BUILD SEPARATE OTHERS DATASET
# ==========================================================

others_records = gen[
    gen["State"] == "Others"
].copy()

if others_records.empty:
    raise ValueError(
        "No Others records found in the source dataset."
    )

others_start = others_records["Month"].min()
others_end = others_records["Month"].max()

others_months = pd.period_range(
    others_start,
    others_end,
    freq="M"
)

others_panel = build_panel(
    records=others_records,
    labels=["Others"],
    months=others_months,
    dataset_name="others"
)

others_file = OUTPUT_DIR / "others_month_analysis.csv"

others_panel.to_csv(
    others_file,
    index=False
)


# ==========================================================
# 9. BUILD MISSING-RECORD REGISTER
# ==========================================================

def create_missing_register(panel, dataset_name):

    entries = []

    for variable in EXPECTED_VARIABLES:

        missing_record = panel[
            ~panel[f"record_present__{variable}"]
        ][["State", "Month"]].copy()

        if not missing_record.empty:
            missing_record["Variable"] = variable
            missing_record["Issue"] = "Missing source record"
            missing_record["Dataset"] = dataset_name
            entries.append(missing_record)

        blank_value = panel[
            panel[f"value_missing__{variable}"]
        ][["State", "Month"]].copy()

        if not blank_value.empty:
            blank_value["Variable"] = variable
            blank_value["Issue"] = "Existing record with blank Value"
            blank_value["Dataset"] = dataset_name
            entries.append(blank_value)

    if not entries:
        return pd.DataFrame(
            columns=[
                "Dataset", "State", "Month",
                "Variable", "Issue"
            ]
        )

    result = pd.concat(entries, ignore_index=True)

    return result[
        ["Dataset", "State", "Month", "Variable", "Issue"]
    ]


missing_register = pd.concat(
    [
        create_missing_register(state_panel, "State/UT"),
        create_missing_register(national_panel, "National"),
        create_missing_register(others_panel, "Others")
    ],
    ignore_index=True
)

missing_file = OUTPUT_DIR / "missing_record_register.csv"

missing_register.to_csv(
    missing_file,
    index=False
)


# ==========================================================
# 10. VALIDATION AND BUILD REPORT
# ==========================================================

report = []

def log(message=""):
    report.append(str(message))


log("ANALYSIS DATASET BUILD REPORT")
log("=" * 70)

log("\nSOURCE")
log("-" * 70)
log(f"Input file: {INPUT_FILE}")
log(f"Original rows: {len(df):,}")
log(f"Selected GWh records: {len(gen):,}")
log(f"Variables: {len(EXPECTED_VARIABLES)}")
log(f"Source duplicates: {duplicate_mask.sum():,}")

log("\nSTATE/UT DATASET")
log("-" * 70)
log(f"States/UTs: {len(state_labels)}")
log(f"Months: {len(state_months)}")
log(f"Expected rows: {len(state_labels) * len(state_months):,}")
log(f"Actual rows: {len(state_panel):,}")
log(f"Period: {STATE_START} to {STATE_END}")

log("\nNATIONAL DATASET")
log("-" * 70)
log(f"Expected months: {len(national_months)}")
log(f"Actual rows: {len(national_panel):,}")
log(f"Period: {NATIONAL_START} to {NATIONAL_END}")

log("\nOTHERS DATASET")
log("-" * 70)
log(f"Expected months: {len(others_months)}")
log(f"Actual rows: {len(others_panel):,}")
log(f"Period: {others_start} to {others_end}")

log("\nMISSINGNESS")
log("-" * 70)
log(f"Missing source records: "
    f"{(missing_register['Issue'] == 'Missing source record').sum():,}")
log(f"Existing records with blank values: "
    f"{(missing_register['Issue'] == 'Existing record with blank Value').sum():,}")

log("\nMETRIC AVAILABILITY — STATE DATASET")
log("-" * 70)

for flag in [
    "total_generation_available",
    "renewable_generation_available",
    "fossil_generation_available",
    "renewable_share_inputs_available",
    "fossil_share_inputs_available",
    "renewable_source_breakdown_available",
    "fossil_source_breakdown_available"
]:
    log(
        f"{flag}: {state_panel[flag].sum():,} / "
        f"{len(state_panel):,} state-months"
    )

log("\nOUTPUT FILES")
log("-" * 70)
log(str(state_file))
log(str(national_file))
log(str(others_file))
log(str(missing_file))

# Structural assertions.
assert len(state_panel) == 36 * 53
assert len(national_panel) == 83
assert len(others_panel) == len(others_months)

assert not state_panel.duplicated(
    ["State", "Month"]
).any()

assert not national_panel.duplicated(
    ["State", "Month"]
).any()

assert not others_panel.duplicated(
    ["State", "Month"]
).any()

assert set(state_panel["State"]) == set(state_labels)

report_text = "\n".join(report)

report_file = OUTPUT_DIR / "03_build_validation.txt"

report_file.write_text(
    report_text,
    encoding="utf-8"
)

print(report_text)
print("\nBuild completed successfully.")
print(f"Validation report: {report_file}")
