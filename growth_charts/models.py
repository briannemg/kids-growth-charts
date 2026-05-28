"""
models.py

Data classes representing a child and their growth measurements.
These are the core data structures used throughout the application.

All measurements are stored internally in metric units (cm, kg) regardless
of the units used at input time. Use growth_charts.units for converting
from US customary units before creating Measurement objects, and for
converting back to US customary units for display.

Fields are optional to support partial measurements (e.g. weight-only
well visits, or head circumference at early visits only). At least one
of height_cm, weight_kg, or head_circumference_cm must be present.

BMI is computed automatically as a property when both height_cm and
weight_kg are present - it is never stored directly.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Measurement:
    """
    A single growth measurement taken at one point in time.
    
    All values are stored in metric units. Use growth_charts.units to
    covert from feet/inches/pounds/ounces before creating this object.
    
    At least one of height_cm, weight_kg, or head_circumference_cm must
    be provided. BMI is calculated automatically from height and weight
    when both are present.
    
    Attributes:
        date (date): The date the measurement was taken.
        age_months (float): The child's age in months at the time of
                            measurement.
        height_cm (float | None): The child's height in centimenters, or
                                  None if not measured.
        weight_kg (float | None): The child's weight in kilograms, or
                                  None if not measured.
        head_circumference_cm (float | None): The child's head circumference
                                              in centimeters, or None if not
                                              measured. Typically only recorded
                                              for children under 24 months.
    """
    
    date: date
    age_months: float
    height_cm: float | None = None
    weight_kg: float | None = None
    head_circumference_cm: float | None = None
    
    def __post_init__(self):
        """Validate measurement values after initialization."""
        if self.age_months < 0:
            raise ValueError("age_months must be non-negative")
        
        if self.height_cm is not None and self.height_cm <= 0:
            raise ValueError("height_cm must be greater than zero")
        if self.weight_kg is not None and self.weight_kg <= 0:
            raise ValueError("weight_kg must be greater than zero")
        if (self.head_circumference_cm is not None
                and self.head_circumference_cm <= 0):
            raise ValueError("head_circumference_cm must be greater than zero")
        
        if (self.height_cm is None
                and self.weight_kg is None
                and self.head_circumference_cm is None):
            raise ValueError(
                "at least one of height_cm, weight_kg, or "
                "head_circumference_cm must be provided"
            )
            
    @property
    def bmi(self) -> float | None:
        """
        Calculate BMI from height and weight.
        
        BMI is computed as weight_kg / (height_m ** 2) and is only
        available when both height_cm and weight_kg are present.
        Typically only clinically relevant for children 24 months and older.

        Returns:
            float | None: BMI rounded to 1 decimal place, or None if
                          height or weight is missing.
        """
        if self.height_cm is None or self.weight_kg is None:
            return None
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m ** 2), 1)
        
        
@dataclass
class Child:
    """
    A child with a growth history of one or more measurements.
    
    Attributes:
        name (str): The child's name.
        sex (str): The child's sex, either 'M' for male or 'F' for female.
        dob (date): The child's date of birth.
        measurements (list[Measurement]): A list of growth measurements,
                                          ordered chronologically. All
                                          measurement values are in metric
                                          units (cm, kg).
    """
    
    name: str
    sex: str
    dob: date
    measurements: list[Measurement] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate child attributes after initialization."""
        if self.sex not in ("M", "F"):
            raise ValueError("sex must be 'M' or 'F'")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        
    def age_months_at(self, measurement_date: date) -> float:
        """
        Calculate the child's age in months at a given date.

        Args:
            measurement_date (date): The date to calculate age at.

        Returns:
            float: Age in months, rounded to one decimal place.
        """
        delta_days = (measurement_date - self.dob).days
        return round(delta_days / 30.4375, 1)
    
    @property
    def latest_measurement(self) -> Measurement | None:
        """
        Return the most recent measurement, or None if there are none.

        Returns:
            Measurement | None: The most recent Measurement object, or None.
        """
        if not self.measurements:
            return None
        return max(self.measurements, key=lambda m:m.date)