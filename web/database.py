"""
database.py

SQLite database setup and helper functions for the growth charts app.

The database has three tables:
    children     - one row per child (name, sex, dob)
    measurements - one row per measurement (height, weight, HC)
    family       - single row for parent heights
    
All date values are stored as TEXT in YYYY-MM-DD format.
All measurements are stored in metric (cm, kg).
"""

import sqlite3
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "growth_charts.db"
DEMO_DB_PATH = BASE_DIR / "demo_growth_charts.db"

def ensure_demo_database() -> None:
    """Create the working database from demo data if no database exists."""
    if not DB_PATH.exists() and DEMO_DB_PATH.exists():
        shutil.copy(DEMO_DB_PATH, DB_PATH)

def get_db():
    """
    Open a connection to the SQLite database.
    
    Sets row_factory to sqlite3.Row so results can be accessed
    by column name (e.g. row["name"]) instead of index (row[0]).
    
    Usage:
        with get_db() as db:
            db.execute("SELECT * FROM children")
    """
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    # Enable foreign key enforcement (off by default in SQLite)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    """
    Create all tables if they don't already exist.
    Safe to call on every startup - won't overwrite existing data.
    """
    ensure_demo_database()
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS children (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT    NOT NULL UNIQUE,
                sex  TEXT    NOT NULL,
                dob  TEXT    NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS measurements (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id              INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
                date                  TEXT    NOT NULL,
                height_cm             REAL,
                weight_kg             REAL,
                head_circumference_cm REAL
            );
            
            CREATE TABLE IF NOT EXISTS family (
                id               INTEGER PRIMARY KEY,
                father_height_cm REAL,
                mother_height_cm REAL
            );
        """)
        
        
# ── Children ──────────────────────────────────────────────────────────────────

def get_all_children():
    """Return all children as a list of dicts, ordered by name."""
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, sex, dob FROM children ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]


def get_child_by_name(name):
    """Return a single child dict by name, or None if not found."""
    with get_db() as db:
        row = db.execute(
            "SELECT id, name, sex, dob FROM children WHERE LOWER(name) = LOWER(?)",
            (name,)
        ).fetchone()
    return dict(row) if row else None


def insert_child(name, sex, dob):
    """
    Insert a new child. Raises sqlite3.IntegrityError if name already exists.
    Returns the new child's id.
    """
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO children (name, sex, dob) VALUES (?, ?, ?)",
            (name, sex, dob)
        )
        return cursor.lastrowid
    

def update_child(original_name, name, sex, dob):
    """
    Update a child's name, sex, and dob.
    Returns the number of rows affected (0 if child not found).
    """
    with get_db() as db:
        cursor = db.execute(
            """UPDATE children
               SET name = ?, sex = ?, dob = ?
               WHERE LOWER(name) = LOWER(?)""",
            (name, sex, dob, original_name)
        )
        return cursor.rowcount
    
    
# ── Measurements ──────────────────────────────────────────────────────────────

def get_measurements(child_name):
    """
    Return all measurements for a child as a list of dicts,
    ordered chronologically.
    """
    with get_db() as db:
        rows = db.execute(
            """SELECT m.id, m.date, m.height_cm, m.weight_kg, m.head_circumference_cm
               FROM measurements m
               JOIN children c ON c.id = m.child_id
               WHERE LOWER(c.name) = LOWER(?)
               ORDER BY m.date""",
            (child_name,)
        ).fetchall()
    return [dict(row) for row in rows]


def insert_measurement(child_name, date, height_cm, weight_kg, hc_cm):
    """
    Insert a new measurement for a child.
    Raises sqlite3.IntegrityError if a measurement for that date already exists.
    """
    child = get_child_by_name(child_name)
    if child is None:
        raise ValueError(f"Child '{child_name}' not found")
    with get_db() as db:
        db.execute(
            """INSERT INTO measurements
               (child_id, date, height_cm, weight_kg, head_circumference_cm)
               VALUES (?, ?, ?, ?, ?)""",
            (child["id"], date, height_cm, weight_kg, hc_cm)
        )
        
        
def update_measurement(child_name, date, height_cm, weight_kg, hc_cm):
    """
    Update an existing measurement.
    Returns the number of rows affected (0 if not found).
    """
    child = get_child_by_name(child_name)
    if child is None:
        raise ValueError(f"Child '{child_name}' not found")
    with get_db() as db:
        cursor = db.execute(
            """UPDATE measurements
               SET height_cm = ?, weight_kg = ?, head_circumference_cm = ?
               WHERE child_id = ? AND date = ?""",
            (height_cm, weight_kg, hc_cm, child["id"], date)
        )
        return cursor.rowcount
    
    
def delete_measurement(child_name, date):
    """
    Delete a measurement by child name and date.
    Returns the number of rows affected (0 if not found).
    """
    child = get_child_by_name(child_name)
    if child is None:
        raise ValueError(f"Child '{child_name}' not found")
    with get_db() as db:
        cursor = db.execute(
            "DELETE FROM measurements WHERE child_id = ? AND date = ?",
            (child["id"], date)
        )
        return cursor.rowcount
    
    
# ── Family ────────────────────────────────────────────────────────────────────

def get_family():
    """Return the family heights as a dict, or empty dict if not set."""
    with get_db() as db:
        row = db.execute(
            "SELECT father_height_cm, mother_height_cm FROM family WHERE id = 1"
        ).fetchone()
    return dict(row) if row else {"father_height_cm": None, "mother_height_cm": None}


def upsert_family(father_cm, mother_cm):
    """
    Insert or update the family heights.
    Uses INSERT OR REPLACE to handle the single-row constraint.
    """
    with get_db() as db:
        db.execute(
            """INSERT INTO family (id, father_height_cm, mother_height_cm)
               VALUES (1, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                    father_height_cm = excluded.father_height_cm,
                    mother_height_cm = excluded.mother_height_cm""",
            (father_cm, mother_cm)
        )