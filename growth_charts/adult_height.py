"""
adult_height.py

Adult height projection calculations.

Three projection methods are provided:

1. Mid-parental height (MPH)
   Uses the average of both parents' heights to estimate genetic potential.
   This is the standard clinical formula used by pediatricians.
   Boys:  (father_cm + mother_cm + 13) / 2
   Girls: (father_cm + mother_cm - 13) / 2
   The 13 cm offset accounts for the average height difference between sexes.
   The expected range is ± 8.5 cm (roughly the 5th-95th percentile range).
   
2. Doubling method
   A rule of thumb based on the developmental milestone that a child's
   height roughly doubles as they mature (per Mayo Clinic).
   Boys:  Double their height at age 2 (24 months).
   Girls: Double their height at 18 months.
   Only applicable when the child's age is near the reference age.
   This method requires no parental height data.
   
3. Percentile projection
   Projects the child's current height percentile forward to age 20 using
   the CDC LMS tables. Assumes the child will maintain their current
   percentile through adulthood - i.e. a child at the 75th percentile
   today is projected to be at the 75th percentile at age 20.
   This method requires no parental height data.
   
Sources:
   Mayo Clinic via Hancock Health:
   https://www.hancockhealth.org/mayo-health-library/child-growth-can-you-predict-adult-height/
"""

import math

from scipy.stats import norm

from growth_charts.percentiles import _get_lms_cdc, get_percentile


# ── Constants ─────────────────────────────────────────────────────────────────

# Age used for adult height projection (months) - end of CDC growth charts
ADULT_AGE_MONTHS = 240.0  # 20 years

# Mid-parental height sex offset in cm
MPH_OFFSET_CM = 13.0

# Mid-parental height uncertainty range (± cm, covers ~85% of children)
MPH_RANGE_CM = 8.5

# Ages at which height is doubled to project adult height
DOUBLING_AGE_BOYS_MONTHS = 24.0   # 2 years
DOUBLING_AGE_GIRLS_MONTHS = 18.0  # 18 months


# ── Mid-parental height ───────────────────────────────────────────────────────

def mid_parental_height(
    father_cm: float,
    mother_cm: float,
    sex: str,
) -> float:
    """
    Calculate the mid-parental height (MPH) target for a child.
    
    This is the standard clinical formula for estimating adult height
    based on parental heights. It represents the genetic height potential
    and is independent of the child's current measurements.

    Args:
        father_cm (float): Father's height in centimeters.
        mother_cm (float): Mother's height in centimeters.
        sex (str): Child's sex, 'M' for male or 'F' for female.

    Returns:
        float: Projected adult height in centimeters, rounded to 1 decimal place.
        
    Raises:
        ValueError: If sex is not 'M' or 'F'.
        ValueError: If either parental height is not a positive number.
    """
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    if father_cm <= 0:
        raise ValueError("father_cm must be greater than zero")
    if mother_cm <= 0:
        raise ValueError("mother_cm must be greater than zero")
    
    if sex == "M":
        return round((father_cm + mother_cm + MPH_OFFSET_CM) / 2, 1)
    else:
        return round((father_cm + mother_cm - MPH_OFFSET_CM) / 2, 1)
    
    
def mid_parental_height_range(
    father_cm: float,
    mother_cm: float,
    sex: str,
) -> tuple[float, float]:
    """
    Calculate the expected adult height range based on mid-parental height.
    
    The range is ± 8.5 cm from the MPH target, which covers approximately
    85% of children given their parents' heights.

    Args:
        father_cm (float): Father's height in centimeters.
        mother_cm (float): Mother's height in centimeters.
        sex (str): Child's sex, 'M' for male or 'F' for female.

    Returns:
        tuple[float, float]: A tuple of (low_cm, high_cm) representing
                             the expected adult height range.
    """
    target = mid_parental_height(father_cm, mother_cm, sex)
    return round(target - MPH_RANGE_CM, 1), round(target + MPH_RANGE_CM, 1)


# ── Doubling method ───────────────────────────────────────────────────────────

def doubling_method_age(sex: str) -> float:
    """
    Return the age in months at which the doubling method applies.
    
    Per Mayo Clinic: boys double their height at age 2 (24 months),
    girls double their height at 18 months.

    Args:
        sex (str): 'M' for male or 'F' for female.

    Returns:
        float: Age in months at which height should be doubled.
        
    Raises:
        ValueError: If sex is not 'M' or 'F'.
    """
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    return DOUBLING_AGE_BOYS_MONTHS if sex == "M" else DOUBLING_AGE_GIRLS_MONTHS


def is_near_doubling_age(
    age_months: float,
    sex: str,
    tolerance_months: float = 1.5,
) -> bool:
    """
    Check whether a child's age is close enough to the doubling reference
    age to make the doubling method applicable.

    Args:
        age_months (float): The child's age in months at measurement time.
        sex (str): 'M' for male or 'F' for female.
        tolerance_months (float, optional): How many months either side of the
                                            reference age is considered close enough.
                                            Defaults to 1.5 months (i.e. within a
                                            typical well-visit window).

    Returns:
        bool: True if the child's age is within tolerance of the reference age.
        
    Raises:
        ValueError: If sex is not 'M' or 'F'.
    """
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    reference_age = doubling_method_age(sex)
    return abs(age_months - reference_age) <= tolerance_months


def project_adult_height_doubling(
    height_at_reference_age_cm: float,
    sex: str,
) -> float:
    """
    Project adult height by doubling the child's height at the reference age.
    
    Reference ages (per Mayo Clinic):
      Boys:  24 months (2 years)
      Girls: 18 months
      
    This is a rule-of-thumb estimate only. It should only be called when
    the measurement was taken at or very near the reference age. Use
    is_near_doubling_age() to check eligibility before calling this function.

    Args:
        height_at_reference_age_cm (float): The child's height in centimeters
                                            at the reference age.
        sex (str): 'M' for male or 'F' for female.

    Returns:
        float: Projected adult height in centimeters, rounded to 1 decimal place.
        
    Raises:
        ValueError: If sex is not 'M' or 'F'.
        ValueError: If height is not a positive number.
    """
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    if height_at_reference_age_cm <= 0:
        raise ValueError("height_at_reference_age_cm must be greater than zero")
    return round(height_at_reference_age_cm * 2, 1)


# ── Percentile projection ─────────────────────────────────────────────────────

def project_adult_height_from_percentile(
    current_percentile: float,
    sex: str,
    tables: dict,
) -> float | None:
    """
    Project adult height by carrying the child's current percentile forward
    to age 20 using the CDC stature-for-age LMS table.
    
    This method assumes the child will maintain their current growth percentile
    through the end of the CDC growth charts (age 20 / 240 months).

    Args:
        current_percentile (float): The child's current height percentile (0-100).                                           
        sex (str): Child's sex, 'M' for male or 'F' for female.       
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        float | None: Project adult height in centimeters rounded to 1 decimal
                      place, or None if LMS values cannot be found for age 20.
                      
    Raises:
        ValueError: If current_percentile is not between 0 and 100 exclusive.
    """
    if not (0 < current_percentile < 100):
        raise ValueError("current_percentile must be between 0 and 100 exclusive")
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    
    z = norm.ppf(current_percentile / 100)
    
    df = tables["cdc"]["height"]
    lms = _get_lms_cdc(ADULT_AGE_MONTHS, sex, df)
    
    if lms is None:
        return None
    
    L, m, s = lms
    
    if L != 0:
        projected = float(m * ((1 + L * s * z) ** (1 / L)))
    else:
        projected = float(m * math.exp(s * z))
        
    return round(projected, 1)


def project_adult_height_from_current(
    age_months: float,
    height_cm: float,
    sex: str,
    tables: dict,
) -> float | None:
    current_percentile = get_percentile(age_months, height_cm, sex, "height", tables)
    
    if current_percentile is None:
        return None
    
    # Clamp percentile away from 0 and 100 to avoid infinite z-scores
    current_percentile = max(0.1, min(99.9, current_percentile))
    
    return project_adult_height_from_percentile(current_percentile, sex, tables)