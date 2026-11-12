
from pathlib import Path
from functools import lru_cache
import math

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


# ==================================================
# PATHS AND CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"

DATA_PATH = OUTPUT_DIR / "state_month_analysis.csv"

# Finalized analysis outputs.
# These files are read-only inputs for the API.

DATASETS = {
    "national_monthly": "04_monthly_national_metrics.csv",
    "national_annual": "04_annual_national_summary.csv",

    "national_source_monthly": "07_national_monthly_source_metrics.csv",
    "national_source_annual": "07_national_annual_source_summary.csv",
    "national_source_composition": "07_national_source_composition.csv",

    "state_source_annual": "07_annual_state_source_summary.csv",
    "state_source_period": "07_state_source_period_metrics.csv",
    "state_source_rankings": "07_state_source_rankings.csv",

    "national_capacity": "09_national_capacity_summary.csv",
    "state_capacity_annual": "09_annual_state_capacity_summary.csv",
    "state_capacity_period": "09_state_period_capacity_summary.csv",

    "national_capacity_factors": "10_national_source_capacity_factor_summary.csv",
    "state_capacity_factors": "10_state_source_capacity_factor_summary.csv",
    "capacity_factor_sensitivity": "12_capacity_factor_sensitivity.csv",
    "capacity_factor_rankings": "13_adjusted_state_capacity_factor_rankings.csv",
    "capacity_factor_exclusions": "13_capacity_factor_exclusion_register.csv",

    "emissions_monthly": "15_monthly_state_emissions.csv",
    "emissions_annual": "15_annual_state_emissions_summary.csv",
    "emissions_state_period": "15_state_period_emissions_summary.csv",
    "emissions_comparison": "15_state_emissions_2024_2025_comparison.csv",
}


# ==================================================
# APPLICATION
# ==================================================

app = FastAPI(
    title="Renewable Intelligence API",
    description=(
        "API for India's state-level electricity generation, "
        "renewable resources, capacity and emissions analysis."
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# METRIC CONFIGURATION
# ==================================================

METRICS = {
    "renewable_share": {
        "type": "ratio",
        "numerator": "Renewables",
        "denominator": "Total Generation",
        "availability": "renewable_share_inputs_available",
        "unit": "%"
    },
    "fossil_share": {
        "type": "ratio",
        "numerator": "Fossil",
        "denominator": "Total Generation",
        "availability": "fossil_share_inputs_available",
        "unit": "%"
    },
    "renewable_generation": {
        "type": "sum",
        "column": "Renewables",
        "availability": "renewable_generation_available",
        "unit": "GWh"
    },
    "solar_generation": {
        "type": "sum",
        "column": "Solar",
        "availability": "record_present__Solar",
        "unit": "GWh"
    },
    "wind_generation": {
        "type": "sum",
        "column": "Wind",
        "availability": "record_present__Wind",
        "unit": "GWh"
    },
    "hydro_generation": {
        "type": "sum",
        "column": "Hydro",
        "availability": "record_present__Hydro",
        "unit": "GWh"
    },
    "bioenergy_generation": {
        "type": "sum",
        "column": "Bioenergy",
        "availability": "record_present__Bioenergy",
        "unit": "GWh"
    }
}


# ==================================================
# DATA LOADING
# ==================================================

def load_state_dataset():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"State analysis dataset not found: {DATA_PATH}"
        )

    data = pd.read_csv(DATA_PATH)

    required_columns = [
        "State",
        "Month",
        "State code",
        "State type",
        "Total Generation",
        "Renewables",
        "Fossil"
    ]

    missing = [
        column for column in required_columns
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns in state_month_analysis.csv: {missing}"
        )

    data["Month"] = data["Month"].astype(str)

    if data.duplicated(["State", "Month"]).any():
        raise ValueError(
            "Duplicate State-Month records found in state_month_analysis.csv."
        )

    return data


@lru_cache(maxsize=None)
def load_output_dataset(dataset_key):
    """
    Load a finalized analysis CSV once and cache it.
    """

    if dataset_key not in DATASETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset: {dataset_key}"
        )

    file_path = OUTPUT_DIR / DATASETS[dataset_key]

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Analysis output not found: {file_path.name}"
        )

    try:
        return pd.read_csv(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read {file_path.name}: {str(exc)}"
        )


df = load_state_dataset()


# ==================================================
# JSON SERIALIZATION HELPERS
# ==================================================

def clean_value(value):
    """
    Convert Pandas / NumPy values into JSON-safe Python values.
    Missing and non-finite values become None, never zero.
    """

    if value is None:
        return None

    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)

    if isinstance(value, np.generic):
        value = value.item()

    if pd.isna(value):
        return None

    if isinstance(value, float) and not math.isfinite(value):
        return None

    return value


def dataframe_records(data):
    """
    Convert a DataFrame into JSON-safe records.
    """

    records = data.to_dict(orient="records")

    return [
        {
            str(key): clean_value(value)
            for key, value in record.items()
        }
        for record in records
    ]


def dataset_response(dataset_key, data):
    return {
        "dataset": dataset_key,
        "row_count": len(data),
        "columns": list(data.columns),
        "records": dataframe_records(data)
    }


# ==================================================
# GENERAL DATASET FILTERS
# ==================================================

def filter_dataset(data, state=None, year=None, source=None):
    """
    Apply optional filters without modifying the original dataset.
    """

    result = data.copy()

    if state is not None:
        state_column = next(
            (
                column for column in result.columns
                if column.lower() == "state"
            ),
            None
        )

        if state_column is None:
            raise HTTPException(
                status_code=400,
                detail="State filtering is not supported by this dataset."
            )

        result = result[
            result[state_column].astype(str).str.lower()
            == state.strip().lower()
        ]

    if year is not None:
        year_column = next(
            (
                column for column in result.columns
                if column.lower() == "year"
            ),
            None
        )

        if year_column is not None:
            result = result[
                result[year_column].astype(str) == str(year)
            ]
        else:
            date_column = next(
                (
                    column for column in ["Month", "Date"]
                    if column in result.columns
                ),
                None
            )

            if date_column is None:
                raise HTTPException(
                    status_code=400,
                    detail="Year filtering is not supported by this dataset."
                )

            result = result[
                result[date_column].astype(str).str.startswith(str(year))
            ]

    if source is not None:
        source_column = next(
            (
                column for column in result.columns
                if column.lower() == "source"
            ),
            None
        )

        if source_column is None:
            raise HTTPException(
                status_code=400,
                detail="Source filtering is not supported by this dataset."
            )

        result = result[
            result[source_column].astype(str).str.lower()
            == source.strip().lower()
        ]

    return result


def serve_dataset(dataset_key, state=None, year=None, source=None):
    data = load_output_dataset(dataset_key)

    filtered = filter_dataset(
        data,
        state=state,
        year=year,
        source=source
    )

    return dataset_response(dataset_key, filtered)


# ==================================================
# DATA AVAILABILITY HELPERS
# ==================================================

def flag_is_true(value):
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes"
    }


def is_valid_number(value):
    if pd.isna(value):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def row_metric_value(row, metric):
    """
    Calculate one metric for one State-Month record.
    Returns None when the required inputs are unavailable.
    """

    if metric not in METRICS:
        return None

    config = METRICS[metric]
    availability_column = config["availability"]

    if availability_column not in row.index:
        return None

    if not flag_is_true(row[availability_column]):
        return None

    if config["type"] == "sum":
        column = config["column"]

        if column not in row.index:
            return None

        value = row[column]

        if not is_valid_number(value):
            return None

        return float(value)

    if config["type"] == "ratio":
        numerator_column = config["numerator"]
        denominator_column = config["denominator"]

        if (
            numerator_column not in row.index
            or denominator_column not in row.index
        ):
            return None

        numerator = row[numerator_column]
        denominator = row[denominator_column]

        if not is_valid_number(numerator):
            return None

        if not is_valid_number(denominator):
            return None

        denominator = float(denominator)

        if denominator <= 0:
            return None

        return float(numerator) / denominator * 100

    return None


# ==================================================
# MAP AGGREGATION
# ==================================================

def aggregate_region(group, metric, expected_months):
    """
    Aggregate monthly records for one region.

    Generation metrics are summed.
    Share metrics are calculated from annual totals.
    Incomplete coverage returns None.
    """

    group = group.sort_values("Month")

    available_values = [
        row_metric_value(row, metric)
        for _, row in group.iterrows()
    ]

    valid_count = sum(
        value is not None
        for value in available_values
    )

    expected_count = len(expected_months)

    observed_months = set(group["Month"].astype(str))
    expected_month_set = set(expected_months)

    complete_calendar_coverage = (
        observed_months == expected_month_set
    )

    if (
        not complete_calendar_coverage
        or valid_count != expected_count
    ):
        return {
            "value": None,
            "months_available": valid_count,
            "months_expected": expected_count
        }

    config = METRICS[metric]

    if config["type"] == "sum":
        value = sum(available_values)

    elif config["type"] == "ratio":
        numerator = group[config["numerator"]].sum()
        denominator = group[config["denominator"]].sum()

        if not is_valid_number(denominator) or denominator <= 0:
            value = None
        else:
            value = float(numerator) / float(denominator) * 100

    else:
        value = None

    return {
        "value": round(value, 4) if value is not None else None,
        "months_available": valid_count,
        "months_expected": expected_count
    }


# ==================================================
# VALIDATION HELPERS
# ==================================================

def validate_metric(metric):
    if metric not in METRICS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported metric.",
                "supported_metrics": list(METRICS.keys())
            }
        )


def validate_period_date(period, date):
    if period == "monthly":
        if len(date) != 7 or date[4] != "-":
            raise HTTPException(
                status_code=400,
                detail="Monthly date must use YYYY-MM format."
            )

        try:
            pd.Period(date, freq="M")
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid month."
            )

    elif period == "annual":
        if len(date) != 4 or not date.isdigit():
            raise HTTPException(
                status_code=400,
                detail="Annual date must use YYYY format."
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="Period must be monthly or annual."
        )


# ==================================================
# HEALTH CHECK AND API INFORMATION
# ==================================================

@app.get("/api/health")
def health_check():
    output_status = {}

    for key, filename in DATASETS.items():
        output_status[key] = {
            "file": filename,
            "available": (OUTPUT_DIR / filename).exists()
        }

    return {
        "status": "healthy",
        "dataset": DATA_PATH.name,
        "rows": len(df),
        "regions": int(df["State"].nunique()),
        "start_month": df["Month"].min(),
        "end_month": df["Month"].max(),
        "analysis_outputs": output_status
    }


@app.get("/api/metrics")
def get_metrics():
    return {
        "metrics": [
            {
                "key": key,
                "unit": config["unit"]
            }
            for key, config in METRICS.items()
        ]
    }


@app.get("/api/dashboard/datasets")
def get_dashboard_datasets():
    """
    Lists all finalized analysis datasets and their availability.
    """

    return {
        "datasets": [
            {
                "key": key,
                "file": filename,
                "available": (OUTPUT_DIR / filename).exists()
            }
            for key, filename in DATASETS.items()
        ]
    }


# ==================================================
# STATE EXPLORER: MAP DATA
# ==================================================

@app.get("/api/map-data")
def get_map_data(
    metric: str = Query(...),
    period: str = Query("monthly"),
    date: str = Query(...)
):
    validate_metric(metric)
    validate_period_date(period, date)

    selected_data = df.copy()

    if period == "monthly":
        selected_data = selected_data[
            selected_data["Month"] == date
        ]

        if selected_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {date}."
            )

        regions = []

        for _, row in selected_data.iterrows():
            value = row_metric_value(row, metric)

            regions.append({
                "state": row["State"],
                "state_code": row["State code"],
                "state_type": row["State type"],
                "value": round(value, 4) if value is not None else None,
                "months_available": int(value is not None),
                "months_expected": 1
            })

    else:
        year = date

        selected_data = selected_data[
            selected_data["Month"].str.startswith(year)
        ]

        if selected_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {year}."
            )

        # Use the calendar months present in the complete dataset
        # for that year, rather than each state's observed months.
        # This also supports partial years such as 2025.
        expected_months = sorted(
            selected_data["Month"].unique().tolist()
        )

        regions = []

        for state, group in selected_data.groupby("State"):
            result = aggregate_region(
                group,
                metric,
                expected_months
            )

            first_row = group.iloc[0]

            regions.append({
                "state": state,
                "state_code": first_row["State code"],
                "state_type": first_row["State type"],
                **result
            })

    regions.sort(key=lambda item: item["state"])

    return {
        "metric": metric,
        "unit": METRICS[metric]["unit"],
        "period": period,
        "date": date,
        "region_count": len(regions),
        "regions": regions
    }


# ==================================================
# STATE EXPLORER: REGIONAL HISTORICAL TREND
# ==================================================

@app.get("/api/regions/{region_name}/trend")
def get_region_trend(
    region_name: str,
    metric: str = Query(...)
):
    validate_metric(metric)

    normalized_name = region_name.strip().lower()

    region_data = df[
        df["State"].str.lower() == normalized_name
    ].sort_values("Month")

    if region_data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Region not found: {region_name}"
        )

    observations = []

    for _, row in region_data.iterrows():
        value = row_metric_value(row, metric)

        observations.append({
            "month": row["Month"],
            "value": round(value, 4) if value is not None else None
        })

    return {
        "region": region_data.iloc[0]["State"],
        "metric": metric,
        "unit": METRICS[metric]["unit"],
        "observations": observations
    }


# ==================================================
# NATIONAL TRENDS
# ==================================================

@app.get("/api/national/monthly-generation")
def national_monthly_generation(
    year: str | None = Query(None)
):
    return serve_dataset(
        "national_monthly",
        year=year
    )


@app.get("/api/national/annual-generation")
def national_annual_generation(
    year: str | None = Query(None)
):
    return serve_dataset(
        "national_annual",
        year=year
    )


@app.get("/api/national/source-monthly")
def national_source_monthly(
    year: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "national_source_monthly",
        year=year,
        source=source
    )


@app.get("/api/national/source-annual")
def national_source_annual(
    year: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "national_source_annual",
        year=year,
        source=source
    )


@app.get("/api/national/source-composition")
def national_source_composition(
    source: str | None = Query(None)
):
    return serve_dataset(
        "national_source_composition",
        source=source
    )


# ==================================================
# RENEWABLE RESOURCES
# ==================================================

@app.get("/api/renewables/state-annual")
def renewable_state_annual(
    state: str | None = Query(None),
    year: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "state_source_annual",
        state=state,
        year=year,
        source=source
    )


@app.get("/api/renewables/state-period")
def renewable_state_period(
    state: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "state_source_period",
        state=state,
        source=source
    )


@app.get("/api/renewables/state-rankings")
def renewable_state_rankings(
    state: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "state_source_rankings",
        state=state,
        source=source
    )


# ==================================================
# CAPACITY
# ==================================================

@app.get("/api/capacity/national")
def national_capacity():
    return serve_dataset("national_capacity")


@app.get("/api/capacity/state-annual")
def state_capacity_annual(
    state: str | None = Query(None),
    year: str | None = Query(None)
):
    return serve_dataset(
        "state_capacity_annual",
        state=state,
        year=year
    )


@app.get("/api/capacity/state-period")
def state_capacity_period(
    state: str | None = Query(None)
):
    return serve_dataset(
        "state_capacity_period",
        state=state
    )


# ==================================================
# CAPACITY FACTORS
# ==================================================

@app.get("/api/capacity-factors/national")
def national_capacity_factors(
    source: str | None = Query(None)
):
    return serve_dataset(
        "national_capacity_factors",
        source=source
    )


@app.get("/api/capacity-factors/state")
def state_capacity_factors(
    state: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "state_capacity_factors",
        state=state,
        source=source
    )


@app.get("/api/capacity-factors/sensitivity")
def capacity_factor_sensitivity(
    source: str | None = Query(None)
):
    return serve_dataset(
        "capacity_factor_sensitivity",
        source=source
    )


@app.get("/api/capacity-factors/rankings")
def capacity_factor_rankings(
    state: str | None = Query(None),
    source: str | None = Query(None)
):
    return serve_dataset(
        "capacity_factor_rankings",
        state=state,
        source=source
    )


@app.get("/api/capacity-factors/exclusions")
def capacity_factor_exclusions(
    state: str | None = Query(None),
    source: str | None = Query(None),
    year: str | None = Query(None)
):
    return serve_dataset(
        "capacity_factor_exclusions",
        state=state,
        source=source,
        year=year
    )


# ==================================================
# EMISSIONS
# ==================================================

@app.get("/api/emissions/monthly")
def emissions_monthly(
    state: str | None = Query(None),
    year: str | None = Query(None)
):
    return serve_dataset(
        "emissions_monthly",
        state=state,
        year=year
    )


@app.get("/api/emissions/annual")
def emissions_annual(
    state: str | None = Query(None),
    year: str | None = Query(None)
):
    return serve_dataset(
        "emissions_annual",
        state=state,
        year=year
    )


@app.get("/api/emissions/state-period")
def emissions_state_period(
    state: str | None = Query(None)
):
    return serve_dataset(
        "emissions_state_period",
        state=state
    )


@app.get("/api/emissions/comparison")
def emissions_comparison(
    state: str | None = Query(None)
):
    return serve_dataset(
        "emissions_comparison",
        state=state
    )
