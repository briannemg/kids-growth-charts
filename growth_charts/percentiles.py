"""
percentiles.py

Percentile calculations using the LMS method from CDC and WHO growth charts.

Chart selection by age and measure:
  Height/Weight:
    WHO - birth to 24 months (0-23.9 months)
    CDC - 24 months and older (24-240 months)
  BMI:
    CDC only - 24 months and older (24-240 months)
  Head Circumference:
    WHO - birth to 24 months
    CDC - 24 months to 36 months
  
The LMS method computes a z-score from three parameters per age/sex:
  L - Box-Cox power transformation
  M - median value
  S - generalized coefficient of variation
  
Z-score formula:
  Z = (((X / M) ** L) - 1) / (L * S)    when L != 0
  Z = ln(X / M) / S                     when L == 0
  
Percentile is then: scipy.stats.norm.cdf(Z) * 100

Sources:
  CDC: https://www.cdc.gov/growthcharts/cdc-data-files.htm
  WHO: https://www.cdc.gov/growthcharts/who-data-files.htm
"""

import math
from pathlib import Path

import pandas as pd
from scipy.stats import norm

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"

# Age boundary (months) - WHO below this, CDC at or above
WHO_CDC_CUTOFF = 24.0

# CDC Sex column encoding
CDC_MALE = 1
CDC_FEMALE = 2

# Maximum age for head circumference reference data (months)
HC_MAX_AGE_MONTHS = 36.0

# Valid measures
VALID_MEASURES = ("height", "weight", "head_circumference", "bmi")


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_cdc_file(filename: str) -> pd.DataFrame:
    """
    Load a CDC LMS CSV file and normalize column names to lowercase.
    
    CDC files contain both sexes with Sex column (1=Male, 2=Female).
    Age is stored in the 'Agemos' column.
    
    Some CDC files contain repeated header rows embedded in the data
    (e.g. bmiagerev.csv). These are handled by coercing columns to
    numeric and dropping any rows that fail to parse.

    Args:
        filename (str): The filename within the data directory.

    Returns:
        pd.DataFrame: Normalized dataframe with lowercase column names.
    """
    path = DATA_DIR / filename
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Coerce key columns to numeric - rows with embedded headers will
    # produce NaN and get dropped
    df["sex"] = pd.to_numeric(df["sex"], errors="coerce")
    df["agemos"] = pd.to_numeric(df["agemos"], errors="coerce")
    df = df.dropna(subset=["sex", "agemos"])
    
    # Restore correct types after coercion
    df["sex"] = df["sex"].astype(int)
    df["agemos"] = df["agemos"].astype(float)
    
    return df


def _load_who_file(filename: str) -> pd.DataFrame:
    """
    Load a WHO LMS CSV file and normalize column names.
    
    WHO files contain a single sex. Age is stored in the 'month' column,
    which is renamed to 'agemos' for consistency with CDC files.

    Args:
        filename (str): The filename within the data directory

    Returns:
        pd.DataFrame: Normalized dataframe with 'agemos' age column.
    """
    path = DATA_DIR / filename
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"month": "agemos"})
    return df


def load_all_tables() -> dict:
    """
    Load all CDC and WHO LMS data tables into a dictionary.
    
    Returns a nested dictionary structured as:
        tables["cdc"]["height"]               → DataFrame (both sexes, 24–240 mo)
        tables["cdc"]["weight"]               → DataFrame (both sexes, 24–240 mo)
        tables["cdc"]["bmi"]                  → DataFrame (both sexes, 24–240 mo)
        tables["cdc"]["height_infant"]        → DataFrame (both sexes, 0–36 mo)
        tables["cdc"]["weight_infant"]        → DataFrame (both sexes, 0–36 mo)
        tables["cdc"]["head_circumference"]   → DataFrame (both sexes, 0–36 mo)
        tables["who"]["height"]["M"]          → DataFrame (males, 0–24 mo)
        tables["who"]["height"]["F"]          → DataFrame (females, 0–24 mo)
        tables["who"]["weight"]["M"]          → DataFrame (males, 0–24 mo)
        tables["who"]["weight"]["F"]          → DataFrame (females, 0–24 mo)
        tables["who"]["head_circumference"]["M"] → DataFrame (males, 0–24 mo)
        tables["who"]["head_circumference"]["F"] → DataFrame (females, 0–24 mo)

    Returns:
        dict: Nested dictionary of DataFrames keyed by source, measure, and sex.
        
    Raises:
        FileNotFoundError: If any data file is missing from the data directory.
    """
    return {
        "cdc": {
            "height": _load_cdc_file("cdc_stature_for_age_2_20.csv"),
            "weight": _load_cdc_file("cdc_weight_for_age_2_20.csv"),
            "bmi": _load_cdc_file("cdc_bmi_for_age_2_20.csv"),
            "height_infant": _load_cdc_file("cdc_length_for_age_0_36.csv"),
            "weight_infant": _load_cdc_file("cdc_weight_for_age_0_36.csv"),
            "head_circumference": _load_cdc_file("cdc_head_circumference_0_36.csv"),
        },
        "who": {
            "height": {
                "M": _load_who_file("who_length_for_age_boys.csv"),
                "F": _load_who_file("who_length_for_age_girls.csv"),
            },
            "weight": {
                "M": _load_who_file("who_weight_for_age_boys.csv"),
                "F": _load_who_file("who_weight_for_age_girls.csv"),
            },
            "head_circumference": {
                "M": _load_who_file("who_head_circumference_boys.csv"),
                "F": _load_who_file("who_head_circumference_girls.csv"),
            },
        },
    }
    
    
# ── LMS lookup ────────────────────────────────────────────────────────────────

def _get_lms_cdc(
    age_months: float, sex: str, df: pd.DataFrame
) -> tuple[float, float, float] | None:
    """
    Look up L, M, S values from a CDC dataframe for a given age and sex.
    
    Finds the row with the closest age at or below the given age_months.

    Args:
        age_months (float): The child's age in months.
        sex (str): 'M' for male or 'F' for female.
        df (pd.DataFrame): A CDC LMS dataframe with 'agemos' and 'sex' columns.

    Returns:
        tuple[float, float, float] | None: (L, M, S) values, or None if not found.
    """
    sex_code = CDC_MALE if sex == "M" else CDC_FEMALE
    subset = df[df["sex"] == sex_code]
    subset = subset[subset["agemos"] <= age_months]
    if subset.empty:
        return None
    row = subset.iloc[subset["agemos"].argmax()]
    return float(row["l"]), float(row["m"]), float(row["s"])


def _get_lms_who(
    age_months: float, df: pd.DataFrame
) -> tuple[float, float, float] | None:
    """
    Look up L, M, S values from a WHO dataframe for a given age.
    
    WHO files are already filtered to one sex, so no sex filtering needed.
    Finds the row with the closest age at or below the given age_months.

    Args:
        age_months (float): The child's age in months.
        df (pd.DataFrame): A WHO LMS dataframe with 'agemos' column.

    Returns:
        tuple[float, float, float] | None: (L, M, S) values, or None if not found.
    """
    subset = df[df["agemos"] <= age_months]
    if subset.empty:
        return None
    row = subset.iloc[subset["agemos"].argmax()]
    return float(row["l"]), float(row["m"]), float(row["s"])


# ── LMS math ──────────────────────────────────────────────────────────────────

def _lms_to_zscore(x: float, L: float, m: float, s: float) -> float:
    """
    Convert a measurement to a z-score using the LMS method.

    Args:
        x (float): The measured value (height in cm or weight in kg).
        L (float): The Box-Cox power (L parameter).
        m (float): The median value (M parameter).
        s (float): The generalized coefficient of variation (S parameter).

    Returns:
        float: The z-score corresponding to the measurement.
    """
    if L != 0:
        return (((x / m) ** L) - 1) / (L * s)
    else:
        return math.log(x / m) / s
    
    
def _zscore_to_percentile(z: float) -> float:
    """
    Convert a z-score to a percentile using the standard normal distribution.

    Args:
        z (float): The z-score to convert.

    Returns:
        float: Percentile between 0 and 100, rounded to 1 decimal place.
    """
    return round(float(norm.cdf(z)) * 100, 1)


# ── Public API ────────────────────────────────────────────────────────────────

def get_percentile(
    age_months: float,
    value: float,
    sex: str,
    measure: str,
    tables: dict,
) -> float | None:
    """
    Calculate the percentile for a single measurement.
    
    Automatically selects WHO or CDC tables based on age and measure:
      - height, weight, head_circumference: WHO < 24 months, CDC >= 24 months
      - bmi: CDC only, available from 24 months onward
      - head_circumference: WHO < 24 months, CDC 24–36 months, None beyond 36 months

    Args:
        age_months (float): The child's age in months at measurement time.
        value (float): The measured value in metric units (cm, kg, or
                       kg/m² for BMI).
        sex (str): 'M' for male or 'F' for female.
        measure (str): One of 'height', 'weight', 'head_circumference',
                       or 'bmi'.
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        float | None: Percentile between 0.0 and 100.0, or None if the age
                      is outside the range of available data.
                      
    Raises:
        ValueError: If measure is not 'height' or 'weight'.
        ValueError: If sex is not 'M' or 'F'.
    """
    if measure not in VALID_MEASURES:
        raise ValueError("measure must be one of {VALID_MEASURES}")
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    
    # BMI — CDC only, 24+ months
    if measure == "bmi":
        if age_months < WHO_CDC_CUTOFF:
            return None
        lms = _get_lms_cdc(age_months, sex, tables["cdc"]["bmi"])
        if lms is None:
            return None
        L, m, s = lms
        z = _lms_to_zscore(value, L, m, s)
        return _zscore_to_percentile(z)

    # Head circumference — WHO < 24 months, CDC 24–36 months, None beyond 36 months
    if measure == "head_circumference":
        if age_months > HC_MAX_AGE_MONTHS:
            return None
        if age_months < WHO_CDC_CUTOFF:
            df = tables["who"]["head_circumference"][sex]
            lms = _get_lms_who(age_months, df)
        else:
            df = tables["cdc"]["head_circumference"]
            lms = _get_lms_cdc(age_months, sex, df)
        if lms is None:
            return None
        L, m, s = lms
        z = _lms_to_zscore(value, L, m, s)
        return _zscore_to_percentile(z)

    # Height and weight — WHO < 24 months, CDC >= 24 months
    if age_months < WHO_CDC_CUTOFF:
        df = tables["who"][measure][sex]
        lms = _get_lms_who(age_months, df)
    else:
        df = tables["cdc"][measure]
        lms = _get_lms_cdc(age_months, sex, df)
        
    if lms is None:
        return None
    
    L, m, s = lms
    z = _lms_to_zscore(value, L, m, s)
    return _zscore_to_percentile(z)


def get_percentile_series(
    age_months_list: list[float],
    values: list[float],
    sex: str,
    measure: str,
    tables: dict,
) -> list[float | None]:
    """
    Calculate percentiles for a series of measurements.

    Args:
        age_months_list (list[float]): Ages in months for each measurement.
        values (list[float]): Measured values corresponding to each age.
        sex (str): 'M' for male or 'F' for female.
        measure (str): One of 'height', 'weight', 'head_circumference', or 'bmi'
        tables (dict): The loaded LMS tables from load_all_tables().

    Returns:
        list[float | None]: Percentile for each measurement, or None where
                            the age falls outside available data ranges.
                            
    Raises:
        ValueError: if age_months_list and values have different lengths.
    """
    if len(age_months_list) != len(values):
        raise ValueError("age_months_list and values must have the same length")
    
    return [
        get_percentile(age, val, sex, measure, tables)
        for age, val in zip(age_months_list, values)
    ]