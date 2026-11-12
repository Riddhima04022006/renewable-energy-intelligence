
import pandas as pd

# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Exclude percentage measurements.
# Examine absolute measurements and CO2 intensity separately.
valid_units = ["MW", "GWh", "ktCO2", "gCO2/kWh"]

data = df[
    df["Unit"].isin(valid_units) &
    df["Value"].notna() &
    df["Date"].notna()
].copy()

# Each state-variable combination is a separate time series.
keys = [
    "State", "Category", "Subcategory", "Variable", "Unit"
]

data = data.sort_values(keys + ["Date"]).copy()

data["Series_ID"] = data.groupby(keys).ngroup()

# --------------------------------------------------
# 2. Calculate IQR statistics within each time series
# --------------------------------------------------

grouped = data.groupby(keys)["Value"]

data["Observations"] = grouped.transform("count")
data["Q1"] = grouped.transform(lambda x: x.quantile(0.25))
data["Q3"] = grouped.transform(lambda x: x.quantile(0.75))

data["IQR"] = data["Q3"] - data["Q1"]

# Conventional potential-outlier limits: 1.5 x IQR
data["Lower_1_5_IQR"] = data["Q1"] - 1.5 * data["IQR"]
data["Upper_1_5_IQR"] = data["Q3"] + 1.5 * data["IQR"]

# More extreme-outlier limits: 3 x IQR
data["Lower_3_IQR"] = data["Q1"] - 3 * data["IQR"]
data["Upper_3_IQR"] = data["Q3"] + 3 * data["IQR"]

# --------------------------------------------------
# 3. Define which series can be screened
# --------------------------------------------------

# Require at least 12 numeric monthly observations.
# Do not apply IQR screening when IQR is zero.
data["Screenable"] = (
    (data["Observations"] >= 12) &
    (data["IQR"] > 0)
)

data["Potential_Outlier"] = (
    data["Screenable"] &
    (
        (data["Value"] < data["Lower_1_5_IQR"]) |
        (data["Value"] > data["Upper_1_5_IQR"])
    )
)

data["Extreme_Outlier"] = (
    data["Screenable"] &
    (
        (data["Value"] < data["Lower_3_IQR"]) |
        (data["Value"] > data["Upper_3_IQR"])
    )
)

# --------------------------------------------------
# 4. Coverage summary
# --------------------------------------------------

series_info = (
    data.groupby(keys)
    .agg(
        observations=("Value", "count"),
        iqr=("IQR", "first")
    )
    .reset_index()
)

screenable_series = series_info[
    (series_info["observations"] >= 12) &
    (series_info["iqr"] > 0)
]

short_series = series_info[
    series_info["observations"] < 12
]

zero_iqr_series = series_info[
    (series_info["observations"] >= 12) &
    (series_info["iqr"] == 0)
]

print("=== D9: TEMPORAL OUTLIER SCREENING ===")

print("\n=== SERIES COVERAGE ===")
print("Total series:", len(series_info))
print("Screenable series:", len(screenable_series))
print("Series with fewer than 12 observations:", len(short_series))
print("Series with zero IQR:", len(zero_iqr_series))

# --------------------------------------------------
# 5. Overall outlier counts
# --------------------------------------------------

screened = data[data["Screenable"]].copy()

potential = screened[screened["Potential_Outlier"]]
extreme = screened[screened["Extreme_Outlier"]]

print("\n=== OVERALL RESULTS ===")
print("Screened observations:", len(screened))
print("Potential outliers (1.5 x IQR):", len(potential))
print("Extreme outliers (3 x IQR):", len(extreme))

# --------------------------------------------------
# 6. Results by category
# --------------------------------------------------

print("\n=== RESULTS BY CATEGORY ===")

category_summary = (
    screened.groupby("Category")
    .agg(
        observations=("Value", "count"),
        series=("Series_ID", "nunique"),
        potential_outliers=("Potential_Outlier", "sum"),
        extreme_outliers=("Extreme_Outlier", "sum")
    )
)

print(category_summary.to_string())

# --------------------------------------------------
# 7. Results by variable
# --------------------------------------------------

print("\n=== TOP VARIABLES BY EXTREME OUTLIER COUNT ===")

if len(extreme) > 0:

    variable_summary = (
        extreme.groupby(
            ["Category", "Subcategory", "Variable", "Unit"]
        )
        .size()
        .reset_index(name="extreme_outliers")
        .sort_values("extreme_outliers", ascending=False)
        .head(10)
    )

    print(variable_summary.to_string(index=False))

# --------------------------------------------------
# 8. Show only the 10 most extreme flagged records
# --------------------------------------------------

print("\n=== TOP 10 EXTREME OUTLIER RECORDS ===")

if len(extreme) > 0:

    extreme["Distance_From_Fence"] = extreme.apply(
        lambda row: max(
            row["Lower_3_IQR"] - row["Value"],
            row["Value"] - row["Upper_3_IQR"],
            0
        ),
        axis=1
    )

    columns = [
        "State", "Category", "Variable", "Unit",
        "Date", "Value", "Lower_3_IQR", "Upper_3_IQR"
    ]

    print(
        extreme.nlargest(10, "Distance_From_Fence")
        [columns]
        .to_string(index=False)
    )

else:
    print("No extreme outliers detected.")
