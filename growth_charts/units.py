"""
units.py

Unit conversion utilities for growth measurements.

All measurements are stored internally in metric (cm, kg).
These functions handle conversion from US customary units at input time,
and back to US customary units for display.

Formatting philosophy:
  All formatters are atomic - each returns a single value in a single unit.
  Combine them at the call sites for multi-unit display strings.
  
  Height/Length:
    format_feet_inches(cm)    → "3 ft 7.3 in"
    format_decimal_inches(cm) → "43.3 in"
    format_cm(cm)             → "50.0 cm"
    
  Weight:
    format_lbs_oz(kg)         → "8 lb 4.0 oz"
    format_decimal_lbs(kg)    → "8.3 lb"
    format_kg(kg)             → "3.7 kg"
    
  Age:
    format_age(dob, date)     → "1 year 2 months 12 days"
    
  Ordinals:
    ordinal(n)                → "1st", "2nd", "3rd", "45th"
"""

from datetime import date


# ── Height conversions ────────────────────────────────────────────────────────

def feet_inches_to_cm(feet: int, inches: float) -> float:
    """
    Convert height from feet and inches to centimeters.

    Args:
        feet (int): The feet component of the height (e.g. 3 for 3'2").
        inches (float): The inches component of the height (e.g. 2.0 for 3'2").

    Returns:
        float: Height in centimeters, rounded to 2 decimal places.
    """
    if feet < 0:
        raise ValueError("feet must be non-negative")
    if not (0 <= inches < 12):
        raise ValueError("inches must be between 0 and 11.99")
    total_inches = (feet * 12) + inches
    return round(total_inches * 2.54, 2)


def inches_to_cm(inches: float) -> float:
    """
    Convert height from decimal inches to centimeters.

    Args:
        inches (float): Height in decimal inches (e.g. 38.5).

    Returns:
        float: Height in centimeters, rounded to 2 decimal places.
    """
    if inches <= 0:
        raise ValueError("inches must be greater than zero")
    return round(inches * 2.54, 2)


def cm_to_feet_inches(cm: float) -> tuple[int, float]:
    """
    Convert height from centimeters to feet and inches.

    Args:
        cm (float): Height in centimeters.

    Returns:
        tuple[int, float]: A tuple of (feet, inches) where inches is
                           rounded to 1 decimal place.
    """
    if cm <= 0:
        raise ValueError("cm must be greater than zero")
    total_inches = cm / 2.54
    feet = int(total_inches // 12)
    inches = round(total_inches % 12, 1)
    return feet, inches


def cm_to_inches(cm: float) -> float:
    """
    Convert height from centimeters to decimal inches.

    Args:
        cm (float): Height in centimeters.

    Returns:
        float: Height in decimal inches, rounded to 1 decimal places.
    """
    if cm <= 0:
        raise ValueError("cm must be greater than zero")
    return round(cm / 2.54, 1)


# ── Weight conversions ────────────────────────────────────────────────────────

def lbs_oz_to_kg(pounds: int, ounces: float) -> float:
    """
    Convert weight from pounds and ounces to kilograms.

    Args:
        pounds (int): The pounds component of the weight (e.g. 8 for 8 lb 4 oz).
        ounces (float): The ounces component of the weight (e.g. 4.0 for 8 lb 4 oz).

    Returns:
        float: Weight in kilograms, rounded to 3 decimal places.
    """
    if pounds < 0:
        raise ValueError("pounds must be non-negative")
    if not (0 <= ounces < 16):
        raise ValueError("ounces must be between 0 and 15.99")
    total_oz = (pounds * 16) + ounces
    return round(total_oz * 0.0283495, 3)


def lbs_to_kg(pounds: float) -> float:
    """
    Convert weight from decimal pounds to kilograms.

    Args:
        pounds (float): Weight in decimal pounds (e.g. 22.5).

    Returns:
        float: Weight in kilograms, rounded to 3 decimal places.
    """
    if pounds <= 0:
        raise ValueError("pounds must be greater than zero")
    return round(pounds * 0.453592, 3)


def kg_to_lbs_oz(kg: float) -> tuple[int, float]:
    """
    Convert weight from kilograms to pounds and ounces.

    Args:
        kg (float): Weight in kilograms.

    Returns:
        tuple[int, float]: A tuple of (pounds, ounces) where ounces is
                           rounded to 1 decimal place.
    """
    if kg <= 0:
        raise ValueError("kg must be greater than zero")
    total_oz = kg / 0.0283495
    pounds = int(total_oz // 16)
    ounces = round(total_oz % 16, 1)
    return pounds, ounces


def kg_to_lbs(kg: float) -> float:
    """
    Convert weight from kilograms to decimal pounds.

    Args:
        kg (float): Weight in kilograms.

    Returns:
        float: Weight in decimal pounds, rounded to 2 decimal places.
    """
    if kg <= 0:
        raise ValueError("kg must be greater than zero")
    return round(kg / 0.453592, 2)


# ── Atomic display formatters ─────────────────────────────────────────────────

def format_feet_inches(cm: float) -> str:
    """
    Format a height in cm as feet and inches.

    Args:
        cm (float): Height in centimeters

    Returns:
        str: Formatted string, e.g. "3 ft 7.3 in".
    """
    if cm <= 0:
        raise ValueError("cm must be greater than zero")
    feet, inches = cm_to_feet_inches(cm)
    return f"{feet} ft {inches} in"


def format_decimal_inches(cm: float) -> str:
    """
    Format a height in cm as decimal inches.

    Args:
        cm (float): Height in centimeters.

    Returns:
        str: Formatted string, e.g. "43.3 in"
    """
    if cm <= 0:
        raise ValueError("cm must be greater than zero")
    return f"{cm_to_inches(cm)} in"


def format_cm(cm: float) -> str:
    """
    Format a height or circumference in centimeters.

    Args:
        cm (float): Value in centimeters.

    Returns:
        str: Formatted string, e.g. "50.0 cm"
    """
    if cm <= 0:
        raise ValueError("cm must be greater than zero")
    return f"{round(cm, 1)} cm"


def format_lbs_oz(kg: float) -> str:
    """
    Format a weight in kg as pounds and ounces.

    Args:
        kg (float): Weight in kilograms.

    Returns:
        str: Formatted string, e.g. "8 lb 4.0 oz".
    """
    if kg <= 0:
        raise ValueError("kg must be greater than zero")
    pounds, ounces = kg_to_lbs_oz(kg)
    return f"{pounds} lb {ounces} oz"


def format_decimal_lbs(kg: float) -> str:
    """
    Format a weight in kg as decimal pounds.

    Args:
        kg (float): Weight in kilograms.

    Returns:
        str: Formatted string, e.g. "8.3 lb".
    """
    if kg <= 0:
        raise ValueError("kg must be greater than zero")
    return f"{kg_to_lbs(kg)} lb"

def format_kg(kg: float) -> str:
    """
    Format a weight in kilograms.

    Args:
        kg (float): Weight in kilograms.

    Returns:
        str: Formatted string, e.g. "3.7 kg".
    """
    if kg <= 0:
        raise ValueError("kg must be greater than zero")
    return f"{round(kg, 1)} kg"


# ── Age formatting ────────────────────────────────────────────────────────────

def format_age(dob: date, measurement_date: date) -> str:
    """
    Format the age between two dates as a human-readable string.
    
    Omits any units that are zero. For example:
      - 4 days old         → "4 days"
      - exactly 6 months   → "6 months"
      - 1 year, 2 months   → "1 year 2 months"
      - 1 year, 2m, 12d    → "1 year 2 months 12 days"

    Args:
        dob (date): The child's date of birth.
        measurement_date (date): The date of the measurement.

    Returns:
        str: Human-readable age string with zero units omitted.
        
    Raises:
        ValueError: If measurement_date is before dob.
    """
    if measurement_date < dob:
        raise ValueError("measurement_date cannot be before dob")
    
    # Calculate years, months, days without using dateutil
    years = measurement_date.year - dob.year
    months = measurement_date.month - dob.month
    days = measurement_date.day - dob.day
    
    # Borrow from months if days is negative
    if days < 0:
        months -= 1
        # Find the date exactly (years, months) after dob to get correct
        # days in the partial month, accounting for leap years and varying
        # month lengths
        borrow_year = dob.year + years
        borrow_month = dob.month + months
        if borrow_month <= 0:
            borrow_month += 12
            borrow_year -= 1
        # The reference point is the same day-of-month as dob, but in the
        # borrowed month — days is then measured from there
        try:
            reference = date(borrow_year, borrow_month, dob.day)
        except ValueError:
            # dob.day doesn't exist in borrow_month (e.g. Jan 31 → Feb)
            # use the last day of borrow_month instead
            import calendar
            last_day = calendar.monthrange(borrow_year, borrow_month)[1]
            reference = date(borrow_year, borrow_month, last_day)
        days = (measurement_date - reference).days
        
    # Borrow from years if months is negative
    if months < 0:
        years -= 1
        months += 12
        
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
        
    return " ".join(parts) if parts else "0 days"


# ── Ordinal formatting ────────────────────────────────────────────────────────

def ordinal(n: int) -> str:
    """
    Convert an integer to its ordinal string representation.
    
    Handles the special cases for 11th, 12th, and 13th correctly.
    
    Examples:
      1  → "1st"
      2  → "2nd"
      3  → "3rd"
      4  → "4th"
      11 → "11th"
      12 → "12th"
      21 → "21st"
      22 → "22nd"

    Args:
        n (int): A non-negative integer to convert.

    Returns:
        str: The ordinal string representation.
        
    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    
    # 11, 12, 13 are special cases that always use "th"
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        
    return f"{n}{suffix}"