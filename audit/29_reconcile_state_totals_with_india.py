
import pandas as pd

# --------------------------------------------------
# 1. Load and prepare data
# --------------------------------------------------

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Only additive absolute measurements.
# Exclude percentages and CO2 intensity.
absolute_units = ["MW", "GWh", "ktCO2"]

data = df[df["Unit"].isin(absolute_units)].copy()

keys = ["Date", "Category", "Subcategory", "Variable", "Unit"]

# --------------------------------------------------
# 2. Identify reporting groups
# --------------------------------------------------

india = data[data["State"] == "India Total"].copy()

states = data[
    ~data["State"].isin(["India Total", "Others"])
].copy()

others = data[data["State"] == "Others"].copy()

# Expected geographic State/UT count in each month.
# This accounts for the separate Ladakh reporting period.
expected_states = (
    data[~data["State"].isin(["India Total", "Others"])]
    [["Date", "State"]]
    .drop_duplicates()
    .groupby("Date")
    .size()
    .rename("Expected_States")
    .reset_index()
)

# --------------------------------------------------
# 3. Sum geographic State/UT values
# --------------------------------------------------

state_sum = (
    states.groupby(keys)
    .agg(
        State_Rows=("State", "nunique"),
        Numeric_States=("Value", "count"),
        State_Sum=("Value", lambda x: x.sum(min_count=1))
    )
    .reset_index()
)

# --------------------------------------------------
# 4. Prepare India Total and Others
# --------------------------------------------------

india_total = india[keys + ["State", "Value"]].rename(
    columns={
        "State": "National_Label",
        "Value": "India_Total"
    }
)

others_sum = (
    others.groupby(keys)
    .agg(
        Others_Rows=("State", "nunique"),
        Others_Numeric=("Value", "count"),
        Others_Value=("Value", lambda x: x.sum(min_count=1))
    )
    .reset_index()
)

# --------------------------------------------------
# 5. Match all three reporting groups
# --------------------------------------------------

result = india_total.merge(
    state_sum,
    on=keys,
    how="left"
)

result = result.merge(
    expected_states,
    on="Date",
    how="left"
)

result = result.merge(
    others_sum,
    on=keys,
    how="left"
)

for col in [
    "State_Rows", "Numeric_States",
    "Expected_States", "Others_Rows", "Others_Numeric"
]:
    result[col] = result[col].fillna(0).astype(int)

# Only compare months where every expected geographic
# State/UT has a numeric observation.
result["Complete_States"] = (
    (result["State_Rows"] == result["Expected_States"]) &
    (result["Numeric_States"] == result["Expected_States"]) &
    (result["Expected_States"] > 0)
)

result["Complete_With_Others"] = (
    result["Complete_States"] &
    (result["Others_Rows"] == 1) &
    (result["Others_Numeric"] == 1)
)

# --------------------------------------------------
# 6. Calculate reconciliation differences
# --------------------------------------------------

result["State_Difference"] = (
    result["State_Sum"] - result["India_Total"]
)

result["State_Plus_Others"] = (
    result["State_Sum"] + result["Others_Value"]
)

result["With_Others_Difference"] = (
    result["State_Plus_Others"] - result["India_Total"]
)

# --------------------------------------------------
# 7. Summary function
# --------------------------------------------------

def report_summary(data, complete_col, difference_col, title):

    valid = data[data[complete_col]].copy()
    valid = valid[valid[difference_col].notna()].copy()

    valid["Absolute_Difference"] = valid[difference_col].abs()

    print(f"\n=== {title} ===")
    print("Candidate comparisons:", len(data))
    print("Complete comparisons:", len(valid))
    print("Incomplete comparisons:", len(data) - len(valid))

    if len(valid) == 0:
        print("No complete comparisons available.")
        return

    print("Within 1e-6:", 
          (valid["Absolute_Difference"] <= 1e-6).sum())
    print("Beyond 1e-6:",
          (valid["Absolute_Difference"] > 1e-6).sum())

    print("Median absolute difference:",
          valid["Absolute_Difference"].median())
    print("95th percentile absolute difference:",
          valid["Absolute_Difference"].quantile(0.95))
    print("Maximum absolute difference:",
          valid["Absolute_Difference"].max())

    # Category-wise summary
    print("\n--- BY CATEGORY ---")

    category_summary = (
        valid.groupby("Category")
        .agg(
            comparisons=("Absolute_Difference", "count"),
            median_difference=("Absolute_Difference", "median"),
            p95_difference=("Absolute_Difference",
                            lambda x: x.quantile(0.95)),
            maximum_difference=("Absolute_Difference", "max"),
            beyond_tolerance=("Absolute_Difference",
                              lambda x: (x > 1e-6).sum())
        )
    )

    print(category_summary.to_string())

    # Identify variable series with the largest discrepancies.
    print("\n--- LARGEST VARIABLE-LEVEL DIFFERENCES ---")

    variable_summary = (
        valid.groupby(["Category", "Subcategory", "Variable", "Unit"])
        .agg(
            comparisons=("Absolute_Difference", "count"),
            median_difference=("Absolute_Difference", "median"),
            maximum_difference=("Absolute_Difference", "max")
        )
        .sort_values("maximum_difference", ascending=False)
        .head(10)
    )

    print(variable_summary.to_string())


# --------------------------------------------------
# 8. State/UT sum vs India Total
# --------------------------------------------------

print("=== D8: STATE VS INDIA TOTAL RECONCILIATION ===")

print("\nExpected geographic State/UT count by period:")
print(expected_states.groupby("Expected_States").size().to_string())

print("\nDuplicate India Total keys:",
      india_total.duplicated(keys).sum())

print("Duplicate State/UT keys:",
      states.duplicated(["State"] + keys).sum())

print("Duplicate Others keys:",
      others.duplicated(keys).sum())

report_summary(
    result,
    "Complete_States",
    "State_Difference",
    "STATE/UT SUM VS INDIA TOTAL"
)

# --------------------------------------------------
# 9. State/UT sum + Others vs India Total
# --------------------------------------------------

report_summary(
    result,
    "Complete_With_Others",
    "With_Others_Difference",
    "STATE/UT SUM + OTHERS VS INDIA TOTAL"
)
