
import json
from pathlib import Path
from collections import defaultdict, Counter

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely.validation import explain_validity


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT / "data" / "geography" / "india.geojson"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "geography"
    / "india_states_provisional.geojson"
)

REPORT_FILE = (
    PROJECT_ROOT / "data" / "geography"
    / "01_boundary_validation_report.txt"
)

STATE_FIELD = "st_nm"
YEAR_FIELD = "year"


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def write_report(lines):
    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


def main():

    report = []

    def log(message=""):
        print(message)
        report.append(str(message))

    log("=" * 65)
    log("STATE/UT BOUNDARY DISSOLUTION AND VALIDATION")
    log("=" * 65)

    # --------------------------------------------------
    # 1. LOAD SOURCE
    # --------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        raise ValueError(
            "Input must be a GeoJSON FeatureCollection."
        )

    features = data.get("features", [])

    log("\nSOURCE FILE")
    log("-" * 65)
    log(f"Input: {INPUT_FILE}")
    log(f"Features: {len(features)}")

    # --------------------------------------------------
    # 2. GROUP DISTRICTS BY STATE/UT
    # --------------------------------------------------

    grouped = defaultdict(list)
    source_years = defaultdict(set)
    invalid_features = []
    missing_state_features = []
    geometry_types = Counter()

    for index, feature in enumerate(features):

        properties = feature.get("properties") or {}
        state_name = properties.get(STATE_FIELD)

        if not isinstance(state_name, str) or not state_name.strip():
            missing_state_features.append(index)
            continue

        state_name = state_name.strip()

        geometry_data = feature.get("geometry")

        if not geometry_data:
            invalid_features.append(
                (index, state_name, "Missing geometry")
            )
            continue

        try:
            geom = shape(geometry_data)
        except Exception as exc:
            invalid_features.append(
                (index, state_name, str(exc))
            )
            continue

        geometry_types[geom.geom_type] += 1

        if geom.is_empty:
            invalid_features.append(
                (index, state_name, "Empty geometry")
            )
            continue

        if not geom.is_valid:
            invalid_features.append(
                (
                    index,
                    state_name,
                    explain_validity(geom)
                )
            )
            continue

        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            invalid_features.append(
                (
                    index,
                    state_name,
                    f"Unexpected type: {geom.geom_type}"
                )
            )
            continue

        grouped[state_name].append(geom)

        year = properties.get(YEAR_FIELD)

        if year is not None:
            source_years[state_name].add(str(year))

    log("\nSOURCE GEOMETRY CHECKS")
    log("-" * 65)
    log(f"Geometry types: {dict(geometry_types)}")
    log(f"State labels found: {len(grouped)}")
    log(f"Features without state label: {len(missing_state_features)}")
    log(f"Invalid/problematic features: {len(invalid_features)}")

    if missing_state_features:
        log(
            f"Missing state-label feature indices: "
            f"{missing_state_features[:20]}"
        )

    if invalid_features:
        for item in invalid_features[:20]:
            log(f"Problem: {item}")

        log(
            "\nDISSOLUTION STOPPED: Resolve source geometry "
            "problems before creating the output."
        )

        write_report(report)
        raise ValueError(
            "Invalid or incomplete source geometries found. "
            "See the validation report."
        )

    # --------------------------------------------------
    # 3. DISSOLVE DISTRICTS
    # --------------------------------------------------

    log("\nDISSOLUTION")
    log("-" * 65)

    dissolved_features = []

    for state_name in sorted(grouped):

        state_geometries = grouped[state_name]

        dissolved = unary_union(state_geometries)

        if dissolved.is_empty:
            raise ValueError(
                f"Empty dissolved geometry: {state_name}"
            )

        if not dissolved.is_valid:
            raise ValueError(
                f"Invalid dissolved geometry for {state_name}: "
                f"{explain_validity(dissolved)}"
            )

        if dissolved.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(
                f"Unexpected dissolved geometry type for "
                f"{state_name}: {dissolved.geom_type}"
            )

        years = sorted(
            source_years[state_name],
            key=lambda x: (not x.isdigit(), x)
        )

        dissolved_features.append({
            "type": "Feature",
            "properties": {
                "state_name": state_name,
                "source_feature_count": len(state_geometries),
                "source_years": years
            },
            "geometry": mapping(dissolved)
        })

        log(
            f"{state_name}: "
            f"{len(state_geometries)} source features -> "
            f"{dissolved.geom_type}"
        )

    # --------------------------------------------------
    # 4. FINAL OUTPUT CHECKS
    # --------------------------------------------------

    output_names = [
        feature["properties"]["state_name"]
        for feature in dissolved_features
    ]

    duplicate_names = [
        name for name, count in Counter(output_names).items()
        if count > 1
    ]

    if duplicate_names:
        raise ValueError(
            f"Duplicate output state names: {duplicate_names}"
        )

    output = {
        "type": "FeatureCollection",
        "features": dissolved_features
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            separators=(",", ":")
        )

    # --------------------------------------------------
    # 5. REPORT
    # --------------------------------------------------

    log("\nFINAL VALIDATION")
    log("-" * 65)
    log(f"Output features: {len(dissolved_features)}")
    log(f"Unique state names: {len(set(output_names))}")
    log(f"Duplicate names: {duplicate_names}")
    log(f"Output file: {OUTPUT_FILE}")

    log("\nSOURCE YEAR COVERAGE")
    log("-" * 65)

    all_years = set()

    for state_name in sorted(source_years):
        years = sorted(source_years[state_name])
        all_years.update(years)

        log(
            f"{state_name}: "
            f"{', '.join(years) if years else 'No year metadata'}"
        )

    log(
        f"\nDistinct source years: "
        f"{', '.join(sorted(all_years))}"
    )

    log("\nIMPORTANT")
    log("-" * 65)
    log(
        "This output is a provisional dissolve of the supplied "
        "district geometries."
    )
    log(
        "It does not establish authoritative administrative "
        "boundaries or resolve mixed boundary vintages."
    )
    log(
        "State-name matching against Ember's reporting labels "
        "is a separate validation step."
    )

    write_report(report)

    log(f"\nReport saved: {REPORT_FILE}")
    log("\nDISSOLUTION COMPLETED")


if __name__ == "__main__":
    main()
