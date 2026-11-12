
import pandas as pd

# Read everything as text so pandas does not automatically
# interpret strings such as "NA" as missing values.
df = pd.read_csv(
    "../india_monthly.csv",
    dtype=str,
    keep_default_na=False
)

# Preserve the original Value text and remove surrounding spaces
raw_value = df["Value"].str.strip()

# Identify genuinely empty fields
blank_mask = raw_value.eq("")

# Try converting each value into a number
numeric_value = pd.to_numeric(raw_value, errors="coerce")

# Non-empty values that could not be converted to numbers
nonnumeric_mask = (~blank_mask) & numeric_value.isna()

print("--- VALUE FIELD INVESTIGATION ---")
print("Total records:", len(df))
print("Empty Value fields:", int(blank_mask.sum()))
print("Non-empty, non-numeric Value fields:", int(nonnumeric_mask.sum()))
print("Numeric Value fields:", int(numeric_value.notna().sum()))

# Examine the actual text in non-numeric fields
print("\n--- DISTINCT NON-NUMERIC VALUES ---")
print(
    raw_value[nonnumeric_mask]
    .value_counts()
    .to_string()
)

# Identify which measurement series are affected
affected = df[nonnumeric_mask].copy()

print("\n--- AFFECTED SERIES ---")

if not affected.empty:
    summary = (
        affected.groupby(
            ["Category", "Subcategory", "Variable", "Unit"],
            dropna=False
        )
        .agg(
            affected_records=("Value", "size"),
            affected_states=("State", "nunique")
        )
        .reset_index()
        .sort_values(
            ["affected_records", "Category", "Variable"],
            ascending=[False, True, True]
        )
    )

    print(summary.to_string(index=False))

# Find which states are affected most
print("\n--- STATES WITH MOST AFFECTED RECORDS ---")

if not affected.empty:
    print(
        affected.groupby("State")
        .size()
        .sort_values(ascending=False)
        .to_string()
    )
