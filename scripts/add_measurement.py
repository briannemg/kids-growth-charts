"""
add_measurement.py

Interactive CLI script for managing child growth data files.

Can be used to create a new data file from scratch or to add measurements,
children, and parental heights to an existing file.

Features:
  - Create a new data file if none exists
  - Add new children with name, sex, and date of birth
  - Add growth measurements in US customary or metric units
  - Add head circumference for children under 24 months
  - Update parental heights
  - Returns to the main menu after each action for batch entry
  
Height input options:
  - Feet and inches
  - Decimal inches
  - Centimeters
  
Weight input options:
  - Pounds and ounces
  - Decimal pounds
  - Kilograms
  - Grams
  
Head circumference input options:
  - Decimal inches
  - Centimeters

Usage:
    python scripts/add_measurement.py
    python scripts/add_measurement.py --data data/my_family.json
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to path so growth_charts package is importable
# when running this script directly from the scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from growth_charts.units import(
    feet_inches_to_cm,
    inches_to_cm,
    lbs_oz_to_kg,
    lbs_to_kg,
    format_age,
    format_feet_inches,
    format_decimal_inches,
    format_cm,
    format_lbs_oz,
    format_decimal_lbs,
    format_kg,
)


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_DATA_FILE = Path("data/dummy_data.json")

# Age boundary in months - prompt to head circumference below this
HC_PROMPT_CUTOFF = 36.0


# ── Input helpers ─────────────────────────────────────────────────────────────

def _prompt_date(prompt: str) -> date:
    """
    Prompt the user for a date in YYYY-MM-DD format.
    
    Keeps prompting until a valid date is entered.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        date: The parsed date object.
    """
    while True:
        raw = input(prompt).strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  Invalid date - please use YYYY-MM_DD format (e.g. 2024-03-15)")
            

def _prompt_int(prompt: str, min_val: int = 0, max_val: int = sys.maxsize) -> int:
    """
    Prompt the user for a non-negative integer.
    
    Keeps prompting until a valid integer within [min_val, max_val] is entered.

    Args:
        prompt (str): The prompt to display to the user.
        min_val (int, optional): Minimum acceptable value. Defaults to 0.
        max_val (int, optional): Maximum acceptable value. Defaults to sys.maxsize.

    Returns:
        int: The parsed integer.
    """
    while True:
        raw = input(prompt).strip()
        try:
            val = int(raw)
            if val < min_val or val > max_val:
                print(f"  Value must be between {min_val} and {max_val}")
                continue
            return val
        except ValueError:
            print("  Invalid input - please enter a whole number")
            
            
def _prompt_float(prompt: str, min_val: float = 0.0, max_val: float = float("inf")) -> float:
    """
    Prompt the user for a decimal number within a range.
    
    Keeps prompting until a valid float within [min_val, max_val] is entered.

    Args:
        prompt (str): The prompt to display to the user.
        min_val (float, optional): Minimum acceptable value. Defaults to 0.0.
        max_val (float, optional): Maximum acceptable value. Defaults to infinity.

    Returns:
        float: The parsed float
    """
    while True:
        raw = input(prompt).strip()
        try:
            val = float(raw)
            if val < min_val or val > max_val:
                print(f"  Value must be between {min_val} and {max_val}")
                continue
            return val
        except ValueError:
            print("  Invalid input - please enter a number")
            
            
def _prompt_choice(prompt: str, choices: list[str]) -> str:
    """
    Prompt the user to choose from a list of options.
    
    Keeps prompting until a valid choice is entered. Case-insensitive.

    Args:
        prompt (str): The prompt to display to the user.
        choices (list[str]): Valid choices.

    Returns:
        str: The chosen option in lowercase.
    """
    choices_lower = [c.lower() for c in choices]
    while True:
        raw = input(prompt).strip().lower()
        if raw in choices_lower:
            return raw
        print(f"  Please enter one of: {', '.join(choices)}")
        
        
def _prompt_yes_no(prompt: str) -> bool:
    """
    Prompt the user for a yes/no answer.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        bool: True if yes, False if no.
    """
    return _prompt_choice(prompt, ["y", "n"]) == "y"
        
        
# ── Unit input helpers ────────────────────────────────────────────────────────

def _prompt_height() -> float:
    """
    Prompt the user for a height measurement and convert to centimeters.
    
    Offers feet+inches, decimal inches, or centimeters as input options.

    Returns:
        float: Height in centimeters.
    """
    print("\n Height unit:")
    print("   [1] Feet and inches  (e.g. 3 ft 2 in)")
    print("   [2] Decimal inches   (e.g. 38.5 in)")
    print("   [3] Centimeters      (e.g. 96.5 cm)")
    choice = _prompt_choice("  Enter 1, 2, or 3: ", ["1", "2", "3"])
    
    if choice == "1":
        feet = _prompt_int("  Feet: ", min_val=0)
        inches = _prompt_float("  Inches: ", min_val=0.0, max_val=11.9)
        cm = feet_inches_to_cm(feet, inches)
    elif choice == "2":
        inches = _prompt_float("  Decimal inches: ", min_val=0.1)
        cm = inches_to_cm(inches)
    else:
        cm = _prompt_float("  Centimeters: ", min_val=0.1)
        
    print(f"  → {format_cm(cm)}  ({format_feet_inches(cm)}, {format_decimal_inches(cm)})")
    return cm


def _prompt_weight() -> float:
    """
    Prompt the user for a weight measurement and convert to kilograms.
    
    Offers pounds+ounces, decimal pounds, kilograms, or grams as input options.

    Returns:
        float: Weight in kilograms.
    """
    print("\n Weight unit:")
    print("   [1] Pounds and ounces  (e.g. 8 lb 4 oz)")
    print("   [2] Decimal pounds     (e.g. 22.5 lb)")
    print("   [3] Kilograms          (e.g. 10.2 kg)")
    print("   [4] Grams              (e.g. 3450 g)")
    choice = _prompt_choice("  Enter 1, 2, 3, or 4: ", ["1", "2", "3", "4"])
    
    if choice == "1":
        pounds = _prompt_int("  Pounds: ", min_val=0)
        ounces = _prompt_float("  Ounces: ", min_val=0.0, max_val=15.9)
        kg = lbs_oz_to_kg(pounds, ounces)
    elif choice == "2":
        pounds = _prompt_float("  Decimal pounds: ", min_val=0.1)
        kg = lbs_to_kg(pounds)
    elif choice == "3":
        kg = _prompt_float("  Kilograms: ", min_val=0.1)
    else:
        grams = _prompt_float("  Grams: ", min_val=1.0)
        kg = round(grams / 1000, 3)
        
    print(f"  → {format_kg(kg)} ({format_lbs_oz(kg)}, {format_decimal_lbs(kg)})")
    return kg


def _prompt_head_circumference() -> float:
    """
    Prompt the user for a head circumference measurement and convert
    to centimeters.
    
    Offers decimal inches or centimeters as input options.

    Returns:
        float: Head circumference in centimeters.
    """
    print("\n Head circumference unit:")
    print("   [1] Decimal inches  (e.g. 13.8 in)")
    print("   [2] Centimeters     (e.g. 35.0 cm)")
    choice = _prompt_choice("  Enter 1 or 2: ", ["1", "2"])
    
    if choice == "1":
        inches = _prompt_float("  Decimal inches: ", min_val=0.1)
        cm = inches_to_cm(inches)
    else:
        cm = _prompt_float("  Centimeters: ", min_val=0.1)
        
    print(f"  → {format_cm(cm)}  ({format_decimal_inches(cm)})")
    return cm


# ── File management ───────────────────────────────────────────────────────────

def _create_new_file(filepath: Path) -> dict:
    """
    Create a new empty data file with optional parental heights.
    
    Prompts the user for parental heights and creates the initial JSON
    structure. Does not add any children - that is handled separately.

    Args:
        filepath (Path): Path where the new file will be saved.

    Returns:
        dict: The newly created data dictionary.
    """
    print(f"\n  Creating new data file: {filepath}")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    data: dict = {
        "_note": "Growth data file. Add measurements using scripts/add_measurement.py.",
        "family": {},
        "children": [],
    }
    
    print("\n── Parental heights (optional — used for mid-parental height projection) ──")
    if _prompt_yes_no("  Add father's height? [y/n]: "):
        print("  Father's height:")
        data["family"]["father_height_cm"] = _prompt_height()
        
    if _prompt_yes_no("  Add mother's height? [y/n]: "):
        print("  Mother's height:")
        data["family"]["mother_height_cm"] = _prompt_height()
        
    _save(data, filepath)
    print(f"\n  ✓ Created {filepath}")
    return data


def _save(data: dict, filepath: Path) -> None:
    """
    Save the data dictionary to a JSON file.
    
    Args:
        data (dict): The data to save.
        filepath (Path): The file path to save to.
    """
    with filepath.open("w") as f:
        json.dump(data, f, indent=2)
        
        
# ── Actions ───────────────────────────────────────────────────────────────────

def _add_child(data: dict, filepath: Path) -> None:
    """
    Prompt for a new child's details and add them to the data file.

    Args:
        data (dict): The current data dictionary.
        filepath (Path): The file path to save the updated data to.
    """
    print("\n── Add new child ────────────────────────────────────────────────")
    
    name = ""
    while not name:
        name = input("  Name: ").strip()
        if not name:
            print("  Name cannot be empty")
            
    sex = _prompt_choice("  Sex [M/F]: ", ["M", "F"]).upper()
    dob = _prompt_date("  Date of birth (YYYY-MM-DD): ")
    
    # Check for duplicate name
    existing_names = [c["name"].lower() for c in data.get("children", [])]
    if name.lower() in existing_names:
        print(f"\n Warning: A child named '{name}' already exists.")
        if not _prompt_yes_no("  Continue anyway? [y/n]: "):
            print("  Cancelled.")
            return
        
    new_child = {
        "name": name,
        "sex": sex,
        "dob": str(dob),
        "measurements": [],
    }
    
    data["children"].append(new_child)
    _save(data, filepath)
    print(f"\n  ✓ Added {name} (DOB: {dob})")
    
    
def _update_parental_heights(data: dict, filepath: Path) -> None:
    """
    Prompt for parental heights and update the data file.
    
    Args:
        data (dict): The current data dictionary.
        filepath (Path): The file path to save the updated data to.
    """
    print("\n── Update parental heights ──────────────────────────────────────")
    
    if "family" not in data:
        data["family"] = {}
        
    current_father = data["family"].get("father_height_cm")
    current_mother = data["family"].get("mother_height_cm")
    
    if current_father:
        print(f"  Current father's height: {current_father} cm "
              f"({format_feet_inches(current_father)})")
    if _prompt_yes_no("  Update father's height? [y/n]: "):
        print("  Father's height:")
        data["family"]["father_height_cm"] = _prompt_height()

    if current_mother:
        print(f"  Current mother's height: {current_mother} cm "
              f"({format_feet_inches(current_mother)})")
    if _prompt_yes_no("  Update mother's height? [y/n]: "):
        print("  Mother's height:")
        data["family"]["mother_height_cm"] = _prompt_height()

    _save(data, filepath)
    print("\n  ✓ Parental heights updated")
    
    
def _add_measurement(data: dict, filepath: Path) -> None:
    """
    Prompt for a new measurement and add it to a child's record.
    
    Prompts for head circumference automatically if the child is under
    36 months at the time of measurement.

    Args:
        data (dict): The current data directory.
        filepath (Path): The filepath to save the updated data to.
    """
    children = data.get("children", [])
    if not children:
        print("\n No children found. Please add a child first.")
        return
    
    # ── Select child ──────────────────────────────────────────────────────────
    print("\n── Select child ─────────────────────────────────────────────────")
    for i, child in enumerate(children):
        n = len(child.get("measurements", []))
        print(f"  [{i + 1}] {child['name']}  ({n} measurement{'s' if n != 1 else ''})")
        
    if len(children) == 1:
        selected_index = 0
        print(f"\n Only one child - selecting {children[0]['name']} automatically.")
    else:
        choice = _prompt_int(
            f"\n Select a child [1-{len(children)}]: ",
            min_val=1,
            max_val=len(children),
        )
        selected_index = choice - 1
        
    child = children[selected_index]
    dob = datetime.strptime(child["dob"], "%Y-%m-%d").date()
    print(f"\n Adding measurement for {child['name']} (DOB: {child['dob']})")
    
    # ── Measurement date ──────────────────────────────────────────────────────
    print("\n── Measurement date ─────────────────────────────────────────────")
    if _prompt_yes_no("  Use today's date? [y/n]: "):
        measurement_date = date.today()
        print(f"  → {measurement_date}")
    else:
        measurement_date = _prompt_date("  Enter date (YYYY-MM-DD): ")
        
    if measurement_date < dob:
        print(f"\n Error: Measurement date {measurement_date} is before "
              f"{child['name']}'s date of birth ({dob}).")
        return
    
    # Check for duplicate date
    existing_dates = [m["date"] for m in child.get("measurements", [])]
    if str(measurement_date) in existing_dates:
        print(f"\n  Warning: A measurement for {measurement_date} already exists.")
        if not _prompt_yes_no("  Continue anyway? [y/n]: "):
            print("  Cancelled.")
            return
        
    # Calculate age in months at measurement date
    age_months = round((measurement_date - dob).days / 30.4375, 1)
    age_str = format_age(dob, measurement_date)

    # ── What measurements are available ───────────────────────────────────────
    print("\n── What measurements do you have? ───────────────────────────────")
    print("    [1] Both height and weight")
    print("    [2] Height only")
    print("    [3] Weight only")
    has_choice = _prompt_choice("  Enter 1, 2, or 3: ", ["1", "2", "3"])
    
    height_cm = None
    weight_kg = None
    
    if has_choice in ("1", "2"):
        print("\n── Height ───────────────────────────────────────────────────────")
        height_cm = _prompt_height()
        
    if has_choice in ("1", "3"):
        print("\n── Weight ───────────────────────────────────────────────────────")
        weight_kg = _prompt_weight()
        
    # ── Head circumference — prompt if under HC_PROMPT_CUTOFF months ──────────
    head_circumference_cm = None
    if age_months <= HC_PROMPT_CUTOFF:
        print("\n── Head Circumference ───────────────────────────────────────────")
        print(f"  {child['name']} is {age_str} — head circumference is typically "
              f"measured under 36 months.")
        if _prompt_yes_no("  Do you have a head circumference measurement? [y/n]: "):
            head_circumference_cm = _prompt_head_circumference()

    # ── Confirm ───────────────────────────────────────────────────────────────
    print("\n── Confirm measurement ──────────────────────────────────────────")
    print(f"  Child:    {child['name']}")
    print(f"  Date:     {measurement_date}")
    print(f"  Age:      {age_str}")
    if height_cm is not None:
        print(f"  Height:   {format_cm(height_cm)}"
              f"  ({format_feet_inches(height_cm)}, {format_decimal_inches(height_cm)})")
    if weight_kg is not None:
        print(f"  Weight:   {format_kg(weight_kg)}"
              f"  ({format_lbs_oz(weight_kg)}, {format_decimal_lbs(weight_kg)})")
    if head_circumference_cm is not None:
        print(f"  Head:     {format_cm(head_circumference_cm)}"
              f"  ({format_decimal_inches(head_circumference_cm)})")
    
    if not _prompt_yes_no("\n Save this measurement? [y/n]: "):
        print("  Cancelled.")
        return
    
    # ── Save ──────────────────────────────────────────────────────────────────
    new_measurement: dict = {"date": str(measurement_date)}
    if height_cm is not None:
        new_measurement["height_cm"] = height_cm
    if weight_kg is not None:
        new_measurement["weight_kg"] = weight_kg
    if head_circumference_cm is not None:
        new_measurement["head_circumference_cm"] = head_circumference_cm

    child["measurements"].append(new_measurement)
    child["measurements"].sort(key=lambda m: m["date"])
    _save(data, filepath)

    n = len(child["measurements"])
    print(f"\n  ✓ Measurement saved to {filepath}")
    print(f"  {child['name']} now has {n} measurement{'s' if n != 1 else ''}.\n")
    
    
# ── Main menu ─────────────────────────────────────────────────────────────────

def _print_menu(data: dict, filepath: Path) -> None:
    """
    Print the main menu showing current file status.

    Args:
        data (dict): The current data dictionary.
        filepath (Path): The current data file path.
    """
    children = data.get("children", [])
    family = data.get("family", {})
    has_father = "father_height_cm" in family
    has_mother = "mother_height_cm" in family
    
    print(f"\n{'-' * 60}")
    print(f"  File:     {filepath}")
    print(f"  Children: {len(children)}"
          + (f"  ({', '.join(c['name'] for c in children)})" if children else ""))
    print("  Parents:  "
          + ("Father ✓ " if has_father else "Father - ")
          + ("Mother ✓" if has_mother else "Mother -"))
    print(f"{'-' * 60}")
    print("  [1] Add measurement")
    print("  [2] Add new child")
    print("  [3] Update parental heights")
    print("  [4] Exit")
    print(f"{'-' * 60}")
    

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """
    Main entry point. Loads or creates the data file and runs the main menu.
    """
    parser = argparse.ArgumentParser(
        description="Manage child growth data - add measurements, children, "
                    "and parental heights."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"Path to the JSON data file (default: {DEFAULT_DATA_FILE})",
    )
    args = parser.parse_args()
    
    print("\n╔══════════════════════════════════════════╗")
    print("║       Kids Growth Charts — Data Tool     ║")
    print("╚══════════════════════════════════════════╝")

    # ── Load or create data file ──────────────────────────────────────────────
    if not args.data.exists():
        print(f"\n Data file not found: {args.data}")
        if not _prompt_yes_no("  Create a new data file? [y/n]: "):
            print("  Exiting.")
            sys.exit(0)
        data = _create_new_file(args.data)
        
        # After creating the file, prompt to add first child
        print("\n You'll need at least one child to add measurements.")
        if _prompt_yes_no("  Add a child now? [y/n]: "):
            _add_child(data, args.data)
    else:
        with args.data.open() as f:
            data = json.load(f)
        print(f"\n  Loaded {args.data}")
        
        # If file exists but has no children, prompt to add one
        if not data.get("children"):
            print("\n  No children found in this file.")
            if _prompt_yes_no("  Add a child now? [y/n]: "):
                _add_child(data, args.data)
                
    # ── Main menu loop ────────────────────────────────────────────────────────
    while True:
        _print_menu(data, args.data)
        choice = _prompt_choice("  Enter choice: ", ["1", "2", "3", "4"])
        
        if choice == "1":
            _add_measurement(data, args.data)
        elif choice == "2":
            _add_child(data, args.data)
        elif choice == "3":
            _update_parental_heights(data, args.data)
        elif choice == "4":
            print("\n Goodbye!\n")
            sys.exit(0)
            
            
if __name__ == "__main__":
    main()