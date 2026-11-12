
import pandas as pd

df = pd.read_csv("../india_monthly.csv")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

checks = [
    {
        "category": "Electricity generation",
        "percentage_unit": "%",
        "absolute_unit": "GWh",
        "total_subcategory": "Total",
        "total_variable": "Total Generation"
    },
    {
        "category": "Power sector emissions",
        "percentage_unit": "%",
        "absolute_unit": "ktCO2",
        "total_subcategory": "Total",
        "total_variable": "Total emissions"
    }
]

print("=== D6: PERCENTAGE RECONCILIATION ===")

for check in checks:

    category = check["category"]

    subset = df[df["Category"] == category]

    # Reported percentage values
    pct = subset[
        subset["Unit"] == check["percentage_unit"]
    ][
        ["State", "Date", "Subcategory", "Variable", "Value"]
    ].rename(columns={"Value": "Reported_pct"})

    # Corresponding absolute values
    absolute = subset[
        subset["Unit"] == check["absolute_unit"]
    ][
        ["State", "Date", "Subcategory", "Variable", "Value"]
    ].rename(columns={"Value": "Absolute_value"})

    # Relevant total denominator
    total = subset[
        (subset["Unit"] == check["absolute_unit"]) &
        (subset["Subcategory"] == check["total_subcategory"]) &
        (subset["Variable"] == check["total_variable"])
    ][
        ["State", "Date", "Value"]
    ].rename(columns={"Value": "Total_value"})

    # Match percentage and absolute series
    comparison = pct.merge(
        absolute,
        on=["State", "Date", "Subcategory", "Variable"],
        how="left",
        validate="one_to_one"
    )

    # Attach the relevant state-month total
    comparison = comparison.merge(
        total,
        on=["State", "Date"],
        how="left",
        validate="many_to_one"
    )

    # A comparison is possible only when all values exist
    # and the denominator is positive.
    valid = (
        comparison["Reported_pct"].notna() &
        comparison["Absolute_value"].notna() &
        comparison["Total_value"].notna() &
        (comparison["Total_value"] > 0)
    )

    comparable = comparison[valid].copy()

    unavailable = len(comparison) - len(comparable)

    zero_denominator = (
        comparison["Total_value"].eq(0).sum()
    )

    comparable["Calculated_pct"] = (
        comparable["Absolute_value"] /
        comparable["Total_value"]
    ) * 100

    comparable["Difference_pp"] = (
        comparable["Reported_pct"] -
        comparable["Calculated_pct"]
    ).abs()

    print(f"\n=== {category.upper()} ===")
    print("Total percentage records:", len(comparison))
    print("Comparable records:", len(comparable))
    print("Unavailable comparisons:", unavailable)
    print("Zero denominators:", int(zero_denominator))

    print("\nRESULTS BY SERIES")

    results = []

    for (subcategory, variable), group in comparable.groupby(
        ["Subcategory", "Variable"]
    ):

        diff = group["Difference_pp"]

        results.append({
            "Subcategory": subcategory,
            "Variable": variable,
            "Comparable": len(group),
            "Within 0.01 pp": int((diff <= 0.01).sum()),
            "Within 0.02 pp": int((diff <= 0.02).sum()),
            "Within 0.05 pp": int((diff <= 0.05).sum()),
            "Above 0.05 pp": int((diff > 0.05).sum()),
            "Median difference": diff.median(),
            "95th percentile": diff.quantile(0.95),
            "Maximum difference": diff.max()
        })

    result_df = pd.DataFrame(results)

    if not result_df.empty:
        print(
            result_df.to_string(
                index=False,
                formatters={
                    "Median difference": "{:.6f}".format,
                    "95th percentile": "{:.6f}".format,
                    "Maximum difference": "{:.6f}".format
                }
            )
        )
