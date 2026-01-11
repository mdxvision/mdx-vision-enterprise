"""Utility functions for EHR Proxy"""

def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate Body Mass Index.
    
    Args:
        weight_kg: Weight in kilograms
        height_m: Height in meters
        
    Returns:
        BMI value
    """
    if height_m <= 0:
        raise ValueError("Height must be positive")
    return weight_kg / (height_m ** 2)


def fahrenheit_to_celsius(temp_f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (temp_f - 32) * 5/9


def calculate_egfr(creatinine: float, age: int, is_female: bool) -> float:
    """Calculate estimated GFR using CKD-EPI formula (simplified).
    
    This is a simplified version - production should use full CKD-EPI 2021.
    """
    # Simplified calculation for demo
    base = 142 * min(creatinine / 0.9, 1) ** -0.302
    if is_female:
        base *= 1.012
    base *= 0.9938 ** age
    return round(base, 1)
