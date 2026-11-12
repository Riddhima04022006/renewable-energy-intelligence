
import csv
import json
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parent.parent

GEOJSON_FILE = (
    ROOT / "data" / "geography"
    / "india_states_provisional.geojson"
)

EMBER_FILE = (
    ROOT / "analysis" / "outputs"
    / "state_month_analysis.csv"
)

REPORT_FILE = (
    ROOT / "data" / "geography"
    / "02_ember_region_match_report.txt"
)

# Explicit, auditable geographic name crosswalk.
NAME_CROSSWALK = {
    "Andaman and Nicobar Islands": "Andaman and Nicobar"
}


def normalize(name):
    return " ".join(
        str(name).strip().casefold().split()
    )


def main():

    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    with GEOJSON_FILE.open("r", encoding="utf-8") as f:
        geo_data = json.load(f)

    geo_names = [
        feature["properties"]["state_name"]
        for feature in geo_data["features"]
    ]

    with EMBER_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        if not reader.fieldnames or "State" not in reader.fieldnames:
            raise ValueError("Ember CSV has no State column.")

        ember_names = sorted({
            row["State"].strip()
            for row in reader
            if row.get("State") and row["State"].strip()
        })

    geo_lookup = {
        normalize(name): name
        for name in geo_names
    }

    ember_lookup = {
        normalize(name): name
        for name in ember_names
    }

    mapped_names = []
    mapping_records = []

    for geo_name in geo_names:

        ember_name = NAME_CROSSWALK.get(
            geo_name,
            geo_name
        )

        mapped_names.append(ember_name)

        mapping_records.append({
            "geojson_name": geo_name,
            "ember_name": ember_name,
            "mapping_type": (
                "explicit_alias"
                if geo_name in NAME_CROSSWALK
                else "direct"
            )
        })

    mapped_normalized = [
        normalize(name)
        for name in mapped_names
    ]

    mapped_set = set(mapped_normalized)
    ember_set = set(ember_lookup)

    unmatched_geo = mapped_set - ember_set
    unmatched_ember = ember_set - mapped_set

    duplicate_mappings = {
        name: count
        for name, count in Counter(mapped_normalized).items()
        if count > 1
    }

    log("=" * 65)
    log("EMBER-GEOJSON EXPLICIT CROSSWALK VALIDATION")
    log("=" * 65)

    log("\nCOUNTS")
    log("-" * 65)
    log(f"GeoJSON features: {len(geo_names)}")
    log(f"Unique GeoJSON names: {len(set(map(normalize, geo_names)))}")
    log(f"Ember reporting names: {len(ember_names)}")
    log(f"Mapped reporting names: {len(mapped_set)}")

    log("\nMAPPING REGISTER")
    log("-" * 65)

    for item in mapping_records:
        log(
            f"{item['geojson_name']} -> "
            f"{item['ember_name']} "
            f"[{item['mapping_type']}]"
        )

    log("\nUNMATCHED GEOJSON MAPPINGS")
    log("-" * 65)

    if unmatched_geo:
        for name in sorted(unmatched_geo):
            log(name)
    else:
        log("None")

    log("\nEMBER NAMES WITHOUT GEOGRAPHY")
    log("-" * 65)

    if unmatched_ember:
        for name in sorted(unmatched_ember):
            log(ember_lookup[name])
    else:
        log("None")

    log("\nDUPLICATE MAPPED NAMES")
    log("-" * 65)

    if duplicate_mappings:
        for name, count in duplicate_mappings.items():
            log(f"{name}: {count}")
    else:
        log("None")

    passed = (
        len(geo_names) == 36
        and len(set(map(normalize, geo_names))) == 36
        and len(ember_names) == 36
        and len(mapped_set) == 36
        and not unmatched_geo
        and not unmatched_ember
        and not duplicate_mappings
    )

    log("\nFINAL STATUS")
    log("-" * 65)

    if passed:
        log("PASS: All 36 geographic labels map uniquely to Ember.")
    else:
        log("FAIL: Geographic crosswalk needs further review.")

    log(
        "\nNOTE: A successful name crosswalk does not prove "
        "that geographic boundaries are spatially accurate."
    )

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    log(f"\nReport saved: {REPORT_FILE}")


if __name__ == "__main__":
    main()
