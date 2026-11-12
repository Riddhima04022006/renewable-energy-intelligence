
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# A2: STATE-LEVEL RENEWABLE PENETRATION ANALYSIS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"

INPUT_FILE = OUTPUT_DIR / "state_month_analysis.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

RENEWABLE_COL = "Renewables"
TOTAL_COL = "Total Generation"

EXPECTED_STATES = 36
EXPECTED_MONTHS = 53


def validate_input(df):
    required = {"State", "Month", RENEWABLE_COL, TOTAL_COL}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["Month"] = pd.to_datetime(
        df["Month"].astype(str),
        format="%Y-%m",
        errors="coerce"
    )

    if df["Month"].isna().any():
        raise ValueError("Some Month values could not be parsed.")

    for col in [RENEWABLE_COL, TOTAL_COL]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["State", "Month"]].duplicated().any():
        raise ValueError("Duplicate State-Month records found.")

    if df[["State", RENEWABLE_COL, TOTAL_COL]].isna().any().any():
        raise ValueError("Missing state or required generation values found.")

    if (df[TOTAL_COL] <= 0).any():
        raise ValueError("Total Generation contains zero or negative values.")

    if (df[RENEWABLE_COL] < 0).any():
        raise ValueError("Renewable generation contains negative values.")

    states = df["State"].nunique()
    months = df["Month"].nunique()

    if states != EXPECTED_STATES:
        raise ValueError(
            f"Expected {EXPECTED_STATES} states/UTs, found {states}."
        )

    if months != EXPECTED_MONTHS:
        raise ValueError(
            f"Expected {EXPECTED_MONTHS} months, found {months}."
        )

    expected_rows = EXPECTED_STATES * EXPECTED_MONTHS

    if len(df) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} rows, found {len(df)}."
        )

    return df


def calculate_monthly_metrics(df):
    result = df[["State", "Month", RENEWABLE_COL, TOTAL_COL]].copy()

    result["Renewable_Share_Pct"] = (
        result[RENEWABLE_COL] / result[TOTAL_COL] * 100
    )

    result["Year"] = result["Month"].dt.year
    result["Month_Number"] = result["Month"].dt.month

    return result


def calculate_annual_summary(monthly):
    annual = (
        monthly.groupby(["State", "Year"], as_index=False)
        .agg(
            Months_Observed=("Month", "nunique"),
            Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
            Total_Generation_GWh=(TOTAL_COL, "sum")
        )
    )

    annual["Renewable_Share_Pct"] = (
        annual["Renewable_Generation_GWh"]
        / annual["Total_Generation_GWh"] * 100
    )

    annual["Period_Status"] = np.where(
        annual["Months_Observed"] == 12,
        "Complete calendar year",
        "Partial year"
    )

    return annual


def calculate_period_ranking(monthly):
    ranking = (
        monthly.groupby("State", as_index=False)
        .agg(
            Months_Observed=("Month", "nunique"),
            Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
            Total_Generation_GWh=(TOTAL_COL, "sum")
        )
    )

    ranking["Period_Renewable_Share_Pct"] = (
        ranking["Renewable_Generation_GWh"]
        / ranking["Total_Generation_GWh"] * 100
    )

    ranking = ranking.sort_values(
        "Period_Renewable_Share_Pct",
        ascending=False
    ).reset_index(drop=True)

    ranking.insert(0, "Rank", range(1, len(ranking) + 1))

    return ranking


def calculate_2024_2025_comparison(monthly):
    comparison = monthly[
        monthly["Month"].dt.month.between(1, 11)
        & monthly["Year"].isin([2024, 2025])
    ].copy()

    summary = (
        comparison.groupby(["State", "Year"], as_index=False)
        .agg(
            Months_Observed=("Month", "nunique"),
            Renewable_Generation_GWh=(RENEWABLE_COL, "sum"),
            Total_Generation_GWh=(TOTAL_COL, "sum")
        )
    )

    summary["Renewable_Share_Pct"] = (
        summary["Renewable_Generation_GWh"]
        / summary["Total_Generation_GWh"] * 100
    )

    wide = summary.pivot(
        index="State",
        columns="Year",
        values="Renewable_Share_Pct"
    )

    wide = wide.rename(columns={
        2024: "Jan_Nov_2024_Renewable_Share_Pct",
        2025: "Jan_Nov_2025_Renewable_Share_Pct"
    }).reset_index()

    wide["Change_in_Renewable_Share_pp"] = (
        wide["Jan_Nov_2025_Renewable_Share_Pct"]
        - wide["Jan_Nov_2024_Renewable_Share_Pct"]
    )

    wide = wide.sort_values(
        "Change_in_Renewable_Share_pp",
        ascending=False
    )

    return summary, wide.reset_index(drop=True)


def create_charts(annual, ranking, comparison):
    # 1. Overall period ranking
    plot_data = ranking.sort_values(
        "Period_Renewable_Share_Pct",
        ascending=True
    )

    plt.figure(figsize=(10, 12))
    plt.barh(
        plot_data["State"],
        plot_data["Period_Renewable_Share_Pct"]
    )
    plt.xlabel("Renewable share (%)")
    plt.ylabel("State / UT")
    plt.title(
        "State-wise Renewable Share\n"
        "July 2021 – November 2025"
    )
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "05_state_period_renewable_share.png",
        dpi=200
    )
    plt.close()

    # 2. Annual renewable share by state
    pivot = annual.pivot(
        index="State",
        columns="Year",
        values="Renewable_Share_Pct"
    )

    pivot = pivot.sort_values(
        by=2024,
        ascending=False
    )

    plt.figure(figsize=(12, 12))
    plt.imshow(
        pivot,
        aspect="auto",
        interpolation="nearest"
    )
    plt.colorbar(label="Renewable share (%)")
    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns,
        rotation=45
    )
    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )
    plt.xlabel("Year")
    plt.ylabel("State / UT")
    plt.title("Annual Renewable Share by State / UT")
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "05_state_annual_renewable_share_heatmap.png",
        dpi=200
    )
    plt.close()

    # 3. Change in Jan-Nov renewable share
    plot_data = comparison.sort_values(
        "Change_in_Renewable_Share_pp",
        ascending=True
    )

    plt.figure(figsize=(10, 12))
    plt.barh(
        plot_data["State"],
        plot_data["Change_in_Renewable_Share_pp"]
    )
    plt.axvline(0, linewidth=1)
    plt.xlabel("Change in renewable share (percentage points)")
    plt.ylabel("State / UT")
    plt.title("Change in Renewable Share: Jan-Nov 2024 vs Jan-Nov 2025")
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "05_state_renewable_share_change_2024_2025.png",
        dpi=200
    )
    plt.close()


def main():
    print("=" * 70)
    print("A2: STATE-LEVEL RENEWABLE PENETRATION ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(INPUT_FILE)
    df = validate_input(df)

    print("\nINPUT VALIDATION")
    print(f"Rows: {len(df):,}")
    print(f"States / UTs: {df['State'].nunique()}")
    print(f"Months: {df['Month'].nunique()}")
    print(
        f"Period: {df['Month'].min():%Y-%m} "
        f"to {df['Month'].max():%Y-%m}"
    )
    print("Duplicate State-Month records: 0")
    print("Missing required generation values: 0")

    monthly = calculate_monthly_metrics(df)
    annual = calculate_annual_summary(monthly)
    ranking = calculate_period_ranking(monthly)
    comparison_summary, comparison = (
        calculate_2024_2025_comparison(monthly)
    )

    # Save analysis outputs
    monthly.to_csv(
        OUTPUT_DIR / "05_monthly_state_renewable_share.csv",
        index=False
    )

    annual.to_csv(
        OUTPUT_DIR / "05_annual_state_renewable_share.csv",
        index=False
    )

    ranking.to_csv(
        OUTPUT_DIR / "05_state_period_renewable_ranking.csv",
        index=False
    )

    comparison_summary.to_csv(
        OUTPUT_DIR / "05_jan_nov_2024_2025_state_summary.csv",
        index=False
    )

    comparison.to_csv(
        OUTPUT_DIR / "05_state_renewable_share_change_2024_2025.csv",
        index=False
    )

    create_charts(annual, ranking, comparison)

    # Console report
    print("\nOVERALL PERIOD RANKING")
    print("Metric: Sum of renewable generation / Sum of total generation")
    print("Period: July 2021 – November 2025")

    print(
        ranking[
            ["Rank", "State", "Period_Renewable_Share_Pct"]
        ].to_string(
            index=False,
            formatters={
                "Period_Renewable_Share_Pct": "{:.2f}".format
            }
        )
    )

    print("\nTOP 5 STATES / UTs")
    print(
        ranking.head(5)[
            ["State", "Period_Renewable_Share_Pct"]
        ].to_string(
            index=False,
            formatters={
                "Period_Renewable_Share_Pct": "{:.2f}".format
            }
        )
    )

    print("\nBOTTOM 5 STATES / UTs")
    print(
        ranking.tail(5)[
            ["State", "Period_Renewable_Share_Pct"]
        ].to_string(
            index=False,
            formatters={
                "Period_Renewable_Share_Pct": "{:.2f}".format
            }
        )
    )

    print("\nJAN-NOV 2024 VS JAN-NOV 2025")
    print("Positive change = renewable share increased.")
    print("Negative change = renewable share decreased.")

    print(
        comparison[
            [
                "State",
                "Jan_Nov_2024_Renewable_Share_Pct",
                "Jan_Nov_2025_Renewable_Share_Pct",
                "Change_in_Renewable_Share_pp"
            ]
        ].to_string(
            index=False,
            formatters={
                "Jan_Nov_2024_Renewable_Share_Pct": "{:.2f}".format,
                "Jan_Nov_2025_Renewable_Share_Pct": "{:.2f}".format,
                "Change_in_Renewable_Share_pp": "{:+.2f}".format
            }
        )
    )

    print("\nOUTPUTS")
    print("05_monthly_state_renewable_share.csv")
    print("05_annual_state_renewable_share.csv")
    print("05_state_period_renewable_ranking.csv")
    print("05_jan_nov_2024_2025_state_summary.csv")
    print("05_state_renewable_share_change_2024_2025.csv")
    print("Charts saved in outputs/charts/")

    print("\nA2 analysis completed successfully.")


if __name__ == "__main__":
    main()
