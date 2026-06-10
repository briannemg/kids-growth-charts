"""
app.py

Flask backend for the growth charts web app.
Uses SQLite via database.py instead of the JSON data file.

Endpoints:
    GET  /                                 - serves index.html
    GET  /children                         - returns list of children
    POST /children                         - adds a new child
    PUT  /children/<child_name>            - updates a child's info
    POST /calculate                        - accepts a measurement, returns percentiles
    GET  /history/<child_name>             - returns all measurements with percentiles
    POST /measurements                     - saves a new measurement
    PUT  /measurements/<child_name>/<date> - updates an existing measurement
    DELETE /measurements/<child_name>/<date> - deletes a measurement
    GET  /family                           - returns parent heights
    POST /family                           - updates parent heights
    GET  /charts/<child_name>/<chart_type> - renders a growth chart as PNG
"""

import io
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, jsonify, render_template, request, send_file  # type: ignore # noqa: E402

# ── Path setup ────────────────────────────────────────────────────────────────
# app.py lives in web/, but growth_charts/ is one level up in the project root.

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
from database import (  # noqa: E402
    init_db,
    get_all_children,
    get_child_by_name,
    insert_child,
    update_child,
    get_measurements,
    insert_measurement,
    update_measurement,
    delete_measurement,
    get_family,
    upsert_family,
)

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates", static_folder="static")

# Initialize the database on startup — safe to call every time
init_db()

# Load the LMS reference tables once at startup — they don't change
print("Loading reference tables...")
TABLES = load_all_tables()
print("Ready.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def age_months_at(dob_str: str, measurement_date_str: str) -> float:
    """Calculate age in months between two date strings."""
    dob   = datetime.strptime(dob_str, "%Y-%m-%d").date()
    mdate = datetime.strptime(measurement_date_str, "%Y-%m-%d").date()
    return round((mdate - dob).days / 30.4375, 1)


def build_child_object(child_data: dict, measurements: list[dict]) -> Child:
    """
    Build a Child model object from database rows.
    Used by the chart endpoint to reconstruct the full Child object.
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
                head_circumference_cm=m.get("head_circumference_cm"),
            )
            for m in measurements
        ],
    )


def calc_percentiles(age_months, height_cm, weight_kg, hc_cm, sex):
    """Calculate BMI and all four percentiles from measurement values."""
    bmi = None
    if height_cm and weight_kg:
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)

    percentiles = {
        "height": get_percentile(age_months, height_cm, sex, "height", TABLES)
                  if height_cm else None,
        "weight": get_percentile(age_months, weight_kg, sex, "weight", TABLES)
                  if weight_kg else None,
        "head_circumference": get_percentile(age_months, hc_cm, sex, "head_circumference", TABLES)
                              if hc_cm else None,
        "bmi": get_percentile(age_months, bmi, sex, "bmi", TABLES)
               if bmi else None,
    }
    return bmi, percentiles


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/children", methods=["GET"])
def children_get():
    """
    Return the list of children.

    Response JSON:
        {
            "children": [
                { "name": "Alex", "sex": "M", "dob": "2018-03-15" },
                ...
            ]
        }
    """
    kids = get_all_children()
    result = [{"name": c["name"], "sex": c["sex"], "dob": c["dob"]} for c in kids]
    return jsonify({"children": result})


@app.route("/children", methods=["POST"])
def children_post():
    """
    Add a new child.

    Expected request JSON:
        { "name": "Sam", "sex": "M", "dob": "2020-05-10" }

    Response JSON:
        { "success": true }
    """
    data = request.get_json()

    name = data.get("name", "").strip()
    sex  = data.get("sex", "").strip().upper()
    dob  = data.get("dob", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if sex not in ("M", "F"):
        return jsonify({"error": "Sex must be M or F"}), 400
    if not dob:
        return jsonify({"error": "Date of birth is required"}), 400
    try:
        datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date of birth must be YYYY-MM-DD"}), 400

    try:
        insert_child(name, sex, dob)
    except sqlite3.IntegrityError:
        return jsonify({"error": f"A child named '{name}' already exists"}), 409

    return jsonify({"success": True})


@app.route("/children/<child_name>", methods=["PUT"])
def children_put(child_name):
    """
    Update a child's name, sex, or date of birth.

    Expected request JSON:
        { "name": "Sam", "sex": "F", "dob": "2020-05-10" }

    Response JSON:
        { "success": true, "name": "Sam" }
    """
    data = request.get_json()

    name = data.get("name", "").strip()
    sex  = data.get("sex", "").strip().upper()
    dob  = data.get("dob", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if sex not in ("M", "F"):
        return jsonify({"error": "Sex must be M or F"}), 400
    if not dob:
        return jsonify({"error": "Date of birth is required"}), 400
    try:
        datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date of birth must be YYYY-MM-DD"}), 400

    try:
        rows = update_child(child_name, name, sex, dob)
    except sqlite3.IntegrityError:
        return jsonify({"error": f"A child named '{name}' already exists"}), 409

    if rows == 0:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    return jsonify({"success": True, "name": name})


@app.route("/calculate", methods=["POST"])
def calculate():
    """
    Calculate percentiles for a submitted measurement (does not save).

    Expected request JSON:
        {
            "child":     "Alex",
            "date":      "2024-06-01",
            "height_cm": 118.0,
            "weight_kg": 23.0,
            "hc_cm":     null
        }
    """
    data = request.get_json()

    child_name   = data.get("child")
    measure_date = data.get("date")

    if not child_name or not measure_date:
        return jsonify({"error": "child and date are required"}), 400

    child = get_child_by_name(child_name)
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    height_cm = data.get("height_cm")
    weight_kg = data.get("weight_kg")
    hc_cm     = data.get("hc_cm")

    if height_cm is None and weight_kg is None and hc_cm is None:
        return jsonify({"error": "at least one measurement is required"}), 400

    age_months = age_months_at(child["dob"], measure_date)
    if age_months < 0:
        return jsonify({"error": "Measurement date is before date of birth"}), 400

    bmi, percentiles = calc_percentiles(age_months, height_cm, weight_kg, hc_cm, child["sex"])

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


@app.route("/history/<child_name>")
def history(child_name):
    """
    Return all measurements for a child with percentiles for each.
    """
    child = get_child_by_name(child_name)
    if child is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    measurements = get_measurements(child_name)
    results = []

    for m in measurements:
        age_months = age_months_at(child["dob"], m["date"])
        height_cm  = m.get("height_cm")
        weight_kg  = m.get("weight_kg")
        hc_cm      = m.get("head_circumference_cm")

        bmi, percentiles = calc_percentiles(age_months, height_cm, weight_kg, hc_cm, child["sex"])

        results.append({
            "date":       m["date"],
            "age_months": age_months,
            "height_cm":  height_cm,
            "weight_kg":  weight_kg,
            "hc_cm":      hc_cm,
            "bmi":        bmi,
            "percentiles": percentiles,
        })

    return jsonify({"child": child["name"], "sex": child["sex"], "measurements": results})


@app.route("/measurements", methods=["POST"])
def save_measurement():
    """
    Save a new measurement for a child.

    Expected request JSON:
        {
            "child":     "Alex",
            "date":      "2024-06-01",
            "height_cm": 118.0,
            "weight_kg": 23.0,
            "hc_cm":     null
        }
    """
    data = request.get_json()

    child_name   = data.get("child")
    measure_date = data.get("date")

    if not child_name or not measure_date:
        return jsonify({"error": "child and date are required"}), 400

    if get_child_by_name(child_name) is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    try:
        insert_measurement(
            child_name=child_name,
            date=measure_date,
            height_cm=data.get("height_cm"),
            weight_kg=data.get("weight_kg"),
            hc_cm=data.get("hc_cm"),
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": f"A measurement for {measure_date} already exists"}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({"success": True})


@app.route("/measurements/<child_name>/<measure_date>", methods=["PUT"])
def update_measurement_route(child_name, measure_date):
    """
    Update an existing measurement.

    Expected request JSON:
        { "height_cm": 118.0, "weight_kg": 23.0, "hc_cm": null }
    """
    data = request.get_json()

    if get_child_by_name(child_name) is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    try:
        rows = update_measurement(
            child_name=child_name,
            date=measure_date,
            height_cm=data.get("height_cm"),
            weight_kg=data.get("weight_kg"),
            hc_cm=data.get("hc_cm"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    if rows == 0:
        return jsonify({"error": f"No measurement found for {measure_date}"}), 404

    return jsonify({"success": True})


@app.route("/measurements/<child_name>/<measure_date>", methods=["DELETE"])
def delete_measurement_route(child_name, measure_date):
    """Delete a measurement by child name and date."""
    if get_child_by_name(child_name) is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    try:
        rows = delete_measurement(child_name, measure_date)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    if rows == 0:
        return jsonify({"error": f"No measurement found for {measure_date}"}), 404

    return jsonify({"success": True})


@app.route("/family", methods=["GET"])
def family_get():
    """Return the parent height data."""
    family = get_family()
    return jsonify({
        "father_height_cm": family.get("father_height_cm"),
        "mother_height_cm": family.get("mother_height_cm"),
    })


@app.route("/family", methods=["POST"])
def family_post():
    """
    Update the parent height data.

    Expected request JSON:
        { "father_height_cm": 180.3, "mother_height_cm": 165.1 }
    """
    data = request.get_json()

    father_cm = data.get("father_height_cm")
    mother_cm = data.get("mother_height_cm")

    if not father_cm and not mother_cm:
        return jsonify({"error": "At least one height is required"}), 400

    upsert_family(father_cm, mother_cm)
    return jsonify({"success": True})


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

    Optional query parameters inject a preview measurement (unsaved):
        ?date=2025-03-15&height_cm=118.0&weight_kg=23.0
    """
    child_data = get_child_by_name(child_name)
    if child_data is None:
        return jsonify({"error": f"Child '{child_name}' not found"}), 404

    measurements = get_measurements(child_name)
    child = build_child_object(child_data, measurements)

    # Inject a preview measurement if query parameters are provided
    preview_date   = request.args.get("date")
    preview_height = request.args.get("height_cm", type=float)
    preview_weight = request.args.get("weight_kg", type=float)
    preview_hc     = request.args.get("hc_cm", type=float)

    if preview_date and (preview_height or preview_weight or preview_hc):
        preview_age = age_months_at(child_data["dob"], preview_date)
        existing_dates = [m.date.strftime("%Y-%m-%d") for m in child.measurements]
        if preview_date not in existing_dates:
            child.measurements.append(Measurement(
                date=datetime.strptime(preview_date, "%Y-%m-%d").date(),
                age_months=preview_age,
                height_cm=preview_height,
                weight_kg=preview_weight,
                head_circumference_cm=preview_hc,
            ))
            child.measurements.sort(key=lambda m: m.date)

    # Load family heights for the projection chart
    family = get_family()
    father_cm = family.get("father_height_cm")
    mother_cm = family.get("mother_height_cm")

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

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)