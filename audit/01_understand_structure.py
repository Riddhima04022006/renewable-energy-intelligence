
import pandas as pd

# 1. Load the original dataset
df = pd.read_csv("../india_monthly.csv")

# 2. Understand the table's dimensions
print("Rows:", df.shape[0])
print("Columns:", df.shape[1])

# 3. Inspect the column names and data types
print("\n--- COLUMN TYPES ---")
df.info()

# 4. Look at a few actual records
print("\n--- FIRST 5 ROWS ---")
print(df.head().to_string(index=False))

# 5. Examine the categories in the dataset
for col in ["Category", "Subcategory", "Variable", "Unit"]:
    print(f"\n--- UNIQUE VALUES: {col} ---")
    print(sorted(df[col].dropna().unique().tolist()))
