"""
app.py

Stage 2 Flask backend for the growth charts web app.

Endpoints:
    GET  /            - serves index.html
    GET  /children    - returns the ist of children from the data file
    POST /calculate   - accepts a measurement, returns percentiles
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# app.py lives in web/, but growth_charts/ is one level up in the project root.
# We add the project root to sys.path so Python can find it.

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402
from growth_charts.percentiles import get_percentile, load_all_tables  # noqa: E402

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates", static_folder="static")

# Load the LMS reference tables once at startup - they don't change.
# This takes a moment but means every request is fast.
print("Loading reference tables...")
TABLES = load_all_tables()
print("Ready.")

# Path to the data file
DATA_FILE = PROJECT_ROOT / "data" / "dummy_data.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_children() -> list[dict]:
    """Load children from the JSON data file."""
    with open(DATA_FILE) as f:
        data = json.load(f)
    return data["children"]


def find_child(name: str) -> dict | None:
    """Find a child by name from the data file."""
    for child in load_children():
        if child["name"].lower() == name.lower():
            return child
    return None


def age_months_at(dob_str: str, measurement_date_str: str) -> float:
    """Calculate age in months between two date strings."""
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    mdate = datetime.strptime(measurement_date_str, "%Y-%m-%d").date()
    delta_days = (mdate - dob).days
    return round(delta_days / 30.4375, 1)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/children")
def children():
    """
    Return the list of chidren from the data file.
    
    Response JSON:
        {
            "children": [
                { "name": "Alex", "sex": "M", "dob": "2018-03-15" },
                ...
            ]
        }
    """
    kids = load_children()
    # Only send name, sex, dob - not the full measurement history
    result = [{"name": c["name"], "sex": c["sex"], "dob": c["dob"]} for c in kids]
    return jsonify({"children": result})


@app.route("/calculate", methods=["POST"])
def calculate():
    """
    Calculate percentiles for a submitted measurement.
    
    Expected request JSON:
        {
            "child":      "Alex",
            "date":       "2024-06-01",
            "height_cm":  118.0,        (optional)
            "weight_kg":  23.0,         (optional)
            "hc_cm":      null          (optional)
        }
 
    Response JSON:
        {
            "child":      "Alex",
            "date":       "2024-06-01",
            "age_months": 74.3,
            "height_cm":  118.0,
            "weight_kg":  23.0,
            "hc_cm":      null,
            "bmi":        16.5,
            "percentiles": {
                "height":            62.3,
                "weight":            55.1,
                "head_circumference": null,
                "bmi":               48.2
            }
        }
    """
    data = request.get_json()
    
    # ── Validate required fields ──────────────────────────────────────────────
    child_name = data.get("child")
    measure_date = data.get("date")
    
    if not child_name or not measure_date:
        return jsonify({"error": "child and date are required"}), 400
    
    # ── Look up the child ─────────────────────────────────────────────────────
    child = find_child(child_name)
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404
    
    # ── Read measurements (all optional) ─────────────────────────────────────
    height_cm = data.get("height_cm")
    weight_kg = data.get("weight_kg")
    hc_cm = data.get("hc_cm")
    
    if height_cm is None and weight_kg is None and hc_cm is None:
        return jsonify({"error": "at least one measurement is required"}), 400
    
    # ── Calculate age ─────────────────────────────────────────────────────────
    age_months = age_months_at(child["dob"], measure_date)
    
    if age_months < 0:
        return jsonify({"error": "Measurement date is before date of birth"}), 400
    
    # ── Calculate BMI ─────────────────────────────────────────────────────────
    bmi = None
    if height_cm and weight_kg:
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 1)
        
    sex = child["sex"]
    
    # ── Calculate percentiles ─────────────────────────────────────────────────
    percentiles = {
        "height": get_percentile(age_months, height_cm, sex, "height", TABLES) if height_cm else None,
        "weight": get_percentile(age_months, weight_kg, sex, "weight", TABLES) if weight_kg else None,
        "head_circumference": get_percentile(age_months, hc_cm, sex, "head_circumference", TABLES) if hc_cm else None,
        "bmi": get_percentile(age_months, bmi, sex, "bmi", TABLES) if bmi else None,
    }
    
    return jsonify({
        "child":      child["name"],
        "date":       measure_date,
        "age_months": age_months,
        "height_cm":  height_cm,
        "weight_kg":  weight_kg,
        "hc_cm":      hc_cm,
        "bmi":        bmi,
        "percentiles": percentiles,
    })
    
    
# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)