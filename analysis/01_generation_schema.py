
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_DIR / "india_monthly.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = OUTPUT_DIR / "01_generation_schema.txt"

df = pd.read_csv(
    INPUT_FILE,
    dtype=str,
    keep_default_na=False
)

required = [
    "State", "Date", "Category",
    "Subcategory", "Variable", "Unit", "Value"
]

missing_columns = [c for c in required if c not in df.columns]

if missing_columns:
    raise ValueError(f"Missing expected columns: {missing_columns}")

# Find generation-related category labels without assuming
# their exact spelling.
generation_categories = sorted(
    category
    for category in df["Category"].unique()
    if "generation" in category.strip().lower()
)

print("GENERATION CATEGORY LABELS")
print("=" * 65)

for category in generation_categories:
    print(repr(category))

if not generation_categories:
    raise ValueError(
        "No category containing 'generation' was found. "
        "Check the category labels from script 00."
    )

gen = df[df["Category"].isin(generation_categories)].copy()

print("\nGENERATION DATA OVERVIEW")
print("=" * 65)
print(f"Rows: {len(gen):,}")
print(f"States/labels: {gen['State'].nunique()}")
print(f"Dates: {gen['Date'].nunique()}")
print(f"Subcategories: {gen['Subcategory'].nunique()}")
print(f"Variables: {gen['Variable'].nunique()}")
print(f"Units: {gen['Unit'].nunique()}")

print("\nEXACT VARIABLE / SUBCATEGORY / UNIT COMBINATIONS")
print("=" * 65)

schema = (
    gen.groupby(
        ["Subcategory", "Variable", "Unit"],
        dropna=False
    )
    .agg(
        rows=("Value", "size"),
        states=("State", "nunique"),
        months=("Date", "nunique")
    )
    .reset_index()
    .sort_values(["Subcategory", "Variable", "Unit"])
)

print(schema.to_string(index=False))

print("\nCATEGORY-WISE ROW COUNTS")
print("=" * 65)
print(gen["Subcategory"].value_counts().to_string())

print("\nSTATE-WISE ROW COUNTS")
print("=" * 65)
print(gen["State"].value_counts().to_string())

# Save the schema separately for easy inspection.
schema.to_csv(
    OUTPUT_DIR / "01_generation_schema.csv",
    index=False
)

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("GENERATION DATA OVERVIEW\n")
    f.write("=" * 65 + "\n")
    f.write(f"Rows: {len(gen):,}\n")
    f.write(f"States/labels: {gen['State'].nunique()}\n")
    f.write(f"Dates: {gen['Date'].nunique()}\n\n")
    f.write("VARIABLE SCHEMA\n")
    f.write("=" * 65 + "\n")
    f.write(schema.to_string(index=False))
    f.write("\n")

print(f"\nSchema CSV saved to: {OUTPUT_DIR / '01_generation_schema.csv'}")
print(f"Report saved to: {REPORT_FILE}")
