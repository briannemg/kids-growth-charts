"""
app.py

Flask backend for the growth charts web app.

Endpoints:
    GET  /            - serves index.html
    GET  /children    - returns the ist of children from the data file
    POST /calculate   - accepts a measurement, returns percentiles
    GET  /charts/<child_name>/<chart_type> - renders and returns a growth chart as PNG
"""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, jsonify, render_template, request, send_file  # type: ignore # noqa: E402

# ── Path setup ────────────────────────────────────────────────────────────────
# app.py lives in web/, but growth_charts/ is one level up in the project root.
# We add the project root to sys.path so Python can find it.

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from growth_charts.models import Child, Measurement  # noqa: E402
from growth_charts.percentiles import get_percentile, load_all_tables  # noqa: E402
from growth_charts.plotting import (  # noqa: E402
    plot_bmi_chart,
    plot_growth_chart,
    plot_head_circumference_chart,
    plot_projection_over_time,
)

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

def build_child_object(child_data: dict) -> Child:
    """
    Build a Child model object from raw JSON data.
    
    Used by the chart endpoint to reconstruct the full Child object
    including all historical measurements.
    """
    return Child(
        name=child_data["name"],
        sex=child_data["sex"],
        dob=datetime.strptime(child_data["dob"], "%Y-%m-%d").date(),
        measurements=[
            Measurement(
                date=datetime.strptime(m["date"], "%Y-%m-%d").date(),
                age_months=age_months_at(child_data["dob"], m["date"]),
                height_cm=m.get("height_cm"),
                weight_kg=m.get("weight_kg"),
                head_circumference_cm=m.get("head_circumference"),
            )
            for m in child_data["measurements"]
        ],
    )


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
    
    
@app.route("/measurements", methods=["POST"])
def save_measurement():
    """
    Save a new measurement for a child to the JSON data file.

    Expected request JSON:
        {
            "child":      "Alex",
            "date":       "2024-06-01",
            "height_cm":  118.0,        (optional)
            "weight_kg":  23.0,         (optional)
            "hc_cm":      null          (optional)
        }

    Response JSON:
        { "success": true }
    """
    data = request.get_json()

    child_name = data.get("child")
    measure_date = data.get("date")

    if not child_name or not measure_date:
        return jsonify({"error": "child and date are required"}), 400

    # Load the full data file
    with open(DATA_FILE) as f:
        all_data = json.load(f)

    # Find the child
    child = next(
        (c for c in all_data["children"] if c["name"].lower() == child_name.lower()),
        None
    )
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    # Check for duplicate date
    existing_dates = [m["date"] for m in child["measurements"]]
    if measure_date in existing_dates:
        return jsonify({"error": f"A measurement for {measure_date} already exists"}), 409

    # Build the new measurement — only include fields that were provided
    new_measurement = {"date": measure_date}
    if data.get("height_cm") is not None:
        new_measurement["height_cm"] = data["height_cm"]
    if data.get("weight_kg") is not None:
        new_measurement["weight_kg"] = data["weight_kg"]
    if data.get("hc_cm") is not None:
        new_measurement["head_circumference_cm"] = data["hc_cm"]

    # Append and sort chronologically
    child["measurements"].append(new_measurement)
    child["measurements"].sort(key=lambda m: m["date"])

    # Write back to the file
    with open(DATA_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    return jsonify({"success": True})


@app.route("/measurements/<child_name>/<measure_date>", methods=["PUT"])
def update_measurement(child_name, measure_date):
    """
    Update an existing measurement for a child.
    
    Expected request JSON:
        {
            "height_cm":  118.0,   (optional)
            "weight_kg":  23.0,    (optional)
            "hc_cm":      null     (optional)
        }
        
    Response JSON:
        { "success": true }
    """
    data = request.get_json()
    
    with open(DATA_FILE) as f:
        all_data = json.load(f)
        
    child = next(
        (c for c in all_data["children"] if c["name"].lower() == child_name.lower()),
        None
    )
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404
    
    measurement = next(
        (m for m in child["measurements"] if m["date"] == measure_date),
        None
    )
    
    if measurement is None:
        return jsonify({"error": f"No measurement found for {measure_date}"}), 404
        
    # Update only the fields that were provided
    if data.get("height_cm") is not None:
        measurement["height_cm"] = data["height_cm"]
    elif "height_cm" in data:
        measurement.pop("height_cm", None)
        
    if data.get("weight_kg") is not None:
        measurement["weight_kg"] = data["weight_kg"]
    elif "weight_kg" in data:
        measurement.pop("weight_kg", None)
        
    if data.get("hc_cm") is not None:
        measurement["head_circumference_cm"] = data["hc_cm"]
    elif "hc_cm" in data:
        measurement.pop("head_circumference_cm", None)
        
    with open(DATA_FILE, "w") as f:
        json.dump(all_data, f, indent=2)
        
    return jsonify({"success": True})


@app.route("/measurements/<child_name>/<measure_date>", methods=["DELETE"])
def delete_measurement(child_name, measure_date):
    """
    Delete a measurement for a child.

    Response JSON:
        { "success": true }
    """
    with open(DATA_FILE) as f:
        all_data = json.load(f)

    child = next(
        (c for c in all_data["children"] if c["name"].lower() == child_name.lower()),
        None
    )
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    original_count = len(child["measurements"])
    child["measurements"] = [
        m for m in child["measurements"] if m["date"] != measure_date]

    if len(child["measurements"]) == original_count:
        return jsonify({"error": f"No measurement found for {measure_date}"}), 404

    with open(DATA_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    return jsonify({"success": True})
    
    
@app.route("/history/<child_name>")
def history(child_name):
    """
    Return all measurements for a child with percentiles calculated for each.

    Response JSON:
        {
            "child": "Alex",
            "sex": "M",
            "measurements": [
                {
                    "date": "2024-03-15",
                    "age_months": 72.0,
                    "height_cm": 118.0,
                    "weight_kg": 23.0,
                    "hc_cm": null,
                    "bmi": 16.5,
                    "percentiles": {
                        "height": 71.7,
                        "weight": 77.5,
                        "head_circumference": null,
                        "bmi": 77.8
                    }
                },
                ...
            ]
        }
    """
    child_data = find_child(child_name)
    if child_data is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    sex = child_data["sex"]
    results = []

    for m in child_data["measurements"]:
        age_months = age_months_at(child_data["dob"], m["date"])
        height_cm = m.get("height_cm")
        weight_kg = m.get("weight_kg")
        hc_cm = m.get("head_circumference_cm")

        bmi = None
        if height_cm and weight_kg:
            bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)

        results.append({
            "date": m["date"],
            "age_months": age_months,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "hc_cm": hc_cm,
            "bmi": bmi,
            "percentiles": {
                "height": get_percentile(age_months, height_cm, sex, "height", TABLES)
                          if height_cm else None,
                "weight": get_percentile(age_months, weight_kg, sex, "weight", TABLES)
                          if weight_kg else None,
                "head_circumference": get_percentile(age_months, hc_cm, sex, "head_circumference", TABLES)
                                      if hc_cm else None,
                "bmi": get_percentile(age_months, bmi, sex, "bmi", TABLES)
                       if bmi else None,
            }
        })

    # Sort chronologically
    results.sort(key=lambda x: x["date"])

    return jsonify({"child": child_data["name"], "sex": sex, "measurements": results})
    

@app.route("/charts/<child_name>/<chart_type>")
def chart(child_name, chart_type):
    """
    Render and return a growth chart as a PNG image.
    
    URL examples:
        /charts/Alex/height
        /charts/Alex/weight
        /charts/Alex/head_circumference
        /charts/Alex/bmi
        /charts/Alex/projection
        
    Returns a PNG image directly - use as the src of an <img> tag.
    Returns a JSON error if the child is not found or the chart type
    is not available (e.g. requesting BMI for a child with no height
    or weight data).
    """
    child_data = find_child(child_name)
    if child_data is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404
    
    child = build_child_object(child_data)
    
    # Inject a preview measurement if query parameters are provided.
    # This allows the chart to show an unsaved measurement as a preview point.
    preview_date   = request.args.get("date")
    preview_height = request.args.get("height_cm", type=float)
    preview_weight = request.args.get("weight_kg", type=float)
    preview_hc     = request.args.get("hc_cm", type=float)
    
    if preview_date and (preview_height or preview_weight or preview_hc):
        preview_age = age_months_at(child_data["dob"], preview_date)
        # Only inject if this date isn't already saved
        existing_dates = [m.date.strftime("%Y-%m-%d") for m in child.measurements]
        if preview_date not in existing_dates:
            preview_measurement = Measurement(
                date=datetime.strptime(preview_date, "%Y-%m-%d").date(),
                age_months=preview_age,
                height_cm=preview_height,
                weight_kg=preview_weight,
                head_circumference_cm=preview_hc,
            )
            child.measurements.append(preview_measurement)
            child.measurements.sort(key=lambda m: m.date)
    
    # Load family heights for the projection chart
    with open(DATA_FILE) as f:
        family_data = json.load(f).get("family", {})
    father_cm = family_data.get("father_height_cm")
    mother_cm = family_data.get("mother_height_cm")
    
    # Generate the right chart
    try:
        if chart_type == "height":
            fig = plot_growth_chart(child, "height", TABLES)
        elif chart_type == "weight":
            fig = plot_growth_chart(child, "weight", TABLES)
        elif chart_type == "head_circumference":
            fig = plot_head_circumference_chart(child, TABLES)
        elif chart_type == "bmi":
            fig = plot_bmi_chart(child, TABLES)
        elif chart_type == "projection":
            fig = plot_projection_over_time(child, TABLES, father_cm, mother_cm)
        else:
            return jsonify({"error": f"Unknown chart type '{chart_type}'"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Render the figure to memory and return it as a PNG.
    # We never write to disk - the image goes straight from matplotlib
    # into the HTTP response via an in-memory buffer.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
    
    
# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)