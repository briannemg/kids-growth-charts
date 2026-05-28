"""
data_loader.py

Loads child growth data from a JSON file and converts it into
Child and Measurement model objects.

Expected JSON structure:
  {
    "family": {
      "father_height_cm": 180.3,
      "mother_height_cm": 165.1
    },
    "children": [
      {
        "name": "Alex",
        "sex": "M",
        "dob": "2018-03-15",
        "measurements": [
          {
              "date": "2018-03-15",
              "height_cm": 50.5,
              "weight_kg": 3.4,
              "head_circumference_cm": 34.5
           },
          ...
        ]
      }
    ]
  }
  
All height and circumference values must be in centimeters.
All weight values must be in kilograms.
All fields except 'date' are optional - at least one of height_cm,
weight_kg, or head_circumference_cm must be present per measurement.
BMI is calculated automatically from height and weight when both are
present and is never stored in the JSON.

Use scripts/add_measurement.py to add new measurements - it handles
unit conversion and validation automatically.
"""

import json
from datetime import date, datetime
from pathlib import Path

from growth_charts.models import Child, Measurement


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.

    Args:
        date_str (str): Date string in YYYY-MM-DD format.

    Returns:
        date: Parsed date object.
        
    Raises:
        ValueError: If the string is not in YYYY-MM-DD format.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"Invalid date format '{date_str}' - expected YYYY-MM-DD"
        )
        
        
def _parse_measurement(data: dict, dob: date) -> Measurement | None:
    """
    Parse a single measurement dictionary into a Measurement object.
    
    Automatically calculates age_months from the measurement date and
    the child's date of birth. All measurement fields are optional except
    date - at least one of height_cm, weight_kg, or head_circumference_cm
    must be present or None is returned.
    
    BMI is not stored in the JSON - it is computed automatically by the 
    Measurement class as a property when both height and weight are present.

    Args:
        data (dict): Dictionary with 'date' and optional 'height_cm',
                     'weight_kg', and 'head_circumference_cm' keys.
        dob (date): The child's date of birth, used to calculate age_months.

    Returns:
        Measurement | None: The parsed Measurement object, or None if no
                            measurement values are present.
        
    Raises:
        KeyError: If 'date' key is missing from the dictionary.
        ValueError: If date format is invalid or values fail validation.
    """
    measurement_date = _parse_date(data["date"])
    age_months = round((measurement_date - dob).days / 30.4375, 1)
    
    height_cm = float(data["height_cm"]) if "height_cm" in data else None
    weight_kg = float(data["weight_kg"]) if "weight_kg" in data else None
    head_circumference_cm = (
        float(data["head_circumference_cm"])
        if "head_circumference_cm" in data
        else None
    )
    
    # Skip measurements with no values at all
    if height_cm is None and weight_kg is None and head_circumference_cm is None:
        return None
    
    return Measurement(
        date=measurement_date,
        age_months=age_months,
        height_cm=height_cm,
        weight_kg=weight_kg,
        head_circumference_cm=head_circumference_cm,
    )
    
    
def _parse_child(data: dict) -> Child:
    """
    Parse a single child dictionary into a Child object with measurements.

    Args:
        data (dict): Dictionary with 'name', 'sex', 'dob', and
                     'measurements' keys.

    Returns:
        Child: The parsed Child object with all measurements attached.
        
    Raises:
        KeyError: If required keys are missing from the dictionary.
        ValueError: If any values fail validation.
    """
    dob = _parse_date(data["dob"])
    
    measurements: list[Measurement] = []
    for raw in data.get("measurements", []):
        m = _parse_measurement(raw, dob)
        if m is not None:
            measurements.append(m)
            
    return Child(
        name=data["name"],
        sex=data["sex"],
        dob=dob,
        measurements=measurements,
    )
    
    
# ── Public API ────────────────────────────────────────────────────────────────

def load_data(filepath: Path | str) -> dict:
    """
    Load child growth data from a JSON file.
    
    Parses the JSON file and returns a dictionary containing:
      - 'children': list of Child objects
      - 'father_cm': father's height in cm (float or None)
      - 'mother_cm': mother's height in cm (flaot or None)

    Args:
        filepath (Path | str): Path to the JSON data file.

    Returns:
        dict: A dictionary with keys 'children', 'father_cm', 'mother_cm'.
        
    Raises:
        FileNotFoundError: If the JSON file does not exist.
        ValueError: If the JSON structure is invalid or data fails validation.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    with filepath.open() as f:
        raw = json.load(f)
        
    family = raw.get("family", {})
    children = [_parse_child(c) for c in raw.get("children", [])]
    
    return {
        "children": children,
        "father_cm": family.get("father_height_cm"),
        "mother_cm": family.get("mother_height_cm"),
    }