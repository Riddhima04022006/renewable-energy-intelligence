
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

# Columns proposed to uniquely identify a record
key_columns = [
    "State",
    "Date",
    "Category",
    "Subcategory",
    "Variable",
    "Unit"
]

# Count records that share the same values across all key columns
duplicate_mask = df.duplicated(
    subset=key_columns,
    keep=False
)

duplicate_rows = df[duplicate_mask]

print("Total rows:", len(df))
print("Rows involved in duplicate keys:", len(duplicate_rows))
print(
    "Number of duplicated key combinations:",
    duplicate_rows[key_columns].drop_duplicates().shape[0]
)

if not duplicate_rows.empty:
    print("\n--- EXAMPLE DUPLICATE RECORDS ---")
    print(
        duplicate_rows
        .sort_values(key_columns)
        .head(20)
        .to_string(index=False)
    )
else:
    print("\nNo duplicate key combinations found.")
