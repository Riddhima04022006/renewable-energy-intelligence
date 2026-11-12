
from pathlib import Path
import pandas as pd

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_DIR / "india_monthly.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = OUTPUT_DIR / "00_source_inventory.txt"

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

# Read everything as text. Do not let pandas reinterpret values.
df = pd.read_csv(
    INPUT_FILE,
    dtype=str,
    keep_default_na=False
)

lines = []

def add(text=""):
    lines.append(str(text))

add("SOURCE DATASET INVENTORY")
add("=" * 65)

add(f"File: {INPUT_FILE}")
add(f"Rows: {len(df):,}")
add(f"Columns: {len(df.columns)}")
add(f"Column names: {df.columns.tolist()}")

add("\nCOLUMN-WISE NON-EMPTY COUNTS")
add("-" * 65)

for col in df.columns:
    non_empty = df[col].astype(str).str.strip().ne("").sum()
    add(f"{col}: {non_empty:,} non-empty / {len(df):,}")

add("\nUNIQUE VALUES IN IMPORTANT COLUMNS")
add("-" * 65)

for col in [
    "Category", "Subcategory", "Variable", "Unit"
]:
    if col in df.columns:
        values = sorted(df[col].unique().tolist())
        add(f"\n{col} ({len(values)} unique values):")
        for value in values:
            add(f"  {value!r}")

if "Date" in df.columns:
    dates = pd.to_datetime(df["Date"], errors="coerce")
    add("\nDATE RANGE")
    add("-" * 65)
    add(f"Invalid dates: {dates.isna().sum():,}")
    add(f"Minimum date: {dates.min()}")
    add(f"Maximum date: {dates.max()}")
    add(f"Unique valid dates: {dates.nunique():,}")

if "State" in df.columns:
    states = sorted(df["State"].unique().tolist())
    add("\nSTATE LABELS")
    add("-" * 65)
    add(f"Count: {len(states)}")
    for state in states:
        add(f"  {state}")

if "Value" in df.columns:
    blank_values = df["Value"].astype(str).str.strip().eq("")
    numeric_values = pd.to_numeric(
        df["Value"].astype(str).str.strip(),
        errors="coerce"
    )
    add("\nVALUE FIELD")
    add("-" * 65)
    add(f"Blank values: {blank_values.sum():,}")
    add(f"Numeric values: {numeric_values.notna().sum():,}")
    add(f"Non-blank, non-numeric values: "
        f"{((~blank_values) & numeric_values.isna()).sum():,}")

report = "\n".join(lines)
REPORT_FILE.write_text(report, encoding="utf-8")

print(report)
print(f"\n\nReport saved to: {REPORT_FILE}")
