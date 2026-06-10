"""
migrate.py

One-time migration script — imports all data from dummy_data.json
into the SQLite database.

Run from the project root:
    python web/migrate.py

Safe to re-run: skips children and measurements that already exist.
"""

import json
import sys
from pathlib import Path

# Add project root to path so we can import growth_charts and database
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.database import init_db, insert_child, insert_measurement, upsert_family  # noqa: E402
import sqlite3  # noqa: E402

DATA_FILE = PROJECT_ROOT / "data" / "dummy_data.json"


def migrate():
    print("Initializing database...")
    init_db()

    print(f"Reading {DATA_FILE}...")
    with open(DATA_FILE) as f:
        data = json.load(f)

    # ── Family ────────────────────────────────────────────────────────────────
    family = data.get("family", {})
    father_cm = family.get("father_height_cm")
    mother_cm = family.get("mother_height_cm")
    if father_cm or mother_cm:
        upsert_family(father_cm, mother_cm)
        print("  ✓ Family heights saved")

    # ── Children & measurements ───────────────────────────────────────────────
    for child in data.get("children", []):
        name = child["name"]
        sex  = child["sex"]
        dob  = child["dob"]

        # Insert child (skip if already exists)
        try:
            insert_child(name, sex, dob)
            print(f"  ✓ Added child: {name}")
        except sqlite3.IntegrityError:
            print(f"  — Child already exists, skipping: {name}")

        # Insert measurements
        measurements = child.get("measurements", [])
        skipped = 0
        inserted = 0
        for m in measurements:
            try:
                insert_measurement(
                    child_name=name,
                    date=m["date"],
                    height_cm=m.get("height_cm"),
                    weight_kg=m.get("weight_kg"),
                    hc_cm=m.get("head_circumference_cm"),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1

        print(f"    ✓ {inserted} measurements inserted, {skipped} skipped")

    print("\nMigration complete!")
    print(f"Database: {Path(__file__).parent / 'growth_charts.db'}")


if __name__ == "__main__":
    migrate()