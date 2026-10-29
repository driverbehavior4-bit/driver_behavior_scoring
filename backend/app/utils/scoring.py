"""backend/app/utils/scoring.py — Trip safety scoring formula (pure Python)."""
from typing import List, Dict, Any


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def calculate_trip_score(
    max_speed: float,
    harsh_braking: int,
    harsh_acceleration: int,
    trip_duration: float = 1.0,
    average_speed: float = 0.0,
) -> Dict[str, Any]:
    """
    Formula (identical to ML pipeline):
      speed_score       = clip(100 - (max_speed - 80)*2, 0, 100)
      braking_score     = clip(100 - harsh_braking*10, 0, 100)
      acceleration_score= clip(100 - harsh_acceleration*10, 0, 100)
      trip_safety_score = speed*0.4 + braking*0.3 + accel*0.3
    """
    speed_score  = clip(100.0 - (max_speed - 80.0) * 2.0, 0.0, 100.0)
    braking_score     = clip(100.0 - harsh_braking * 10.0, 0.0, 100.0)
    acceleration_score = clip(100.0 - harsh_acceleration * 10.0, 0.0, 100.0)
    trip_safety_score  = round(speed_score*0.4 + braking_score*0.3 + acceleration_score*0.3, 2)

    if trip_safety_score >= 70:
        risk_label, risk_category = "Low Risk", "Low"
    elif trip_safety_score >= 40:
        risk_label, risk_category = "Moderate Risk", "Moderate"
    else:
        risk_label, risk_category = "High Risk", "High"

    is_high_risk = risk_category == "High"
    total_harsh  = harsh_braking + harsh_acceleration
    safe_dur     = max(trip_duration, 0.01)
    harsh_pm     = round(total_harsh / safe_dur, 4)
    spd_diff     = max(0.0, max_speed - average_speed)

    speed_risk_flag   = speed_score < 60
    braking_risk_flag = braking_score < 60
    accel_risk_flag   = acceleration_score < 60

    factors: List[str] = []
    if speed_risk_flag:
        factors.append(f"Excessive speed (max {max_speed:.0f} km/h)")
    if braking_risk_flag:
        factors.append(f"Frequent harsh braking ({harsh_braking} events)")
    if accel_risk_flag:
        factors.append(f"Frequent harsh acceleration ({harsh_acceleration} events)")
    if not factors:
        factors.append("No significant risk factors")

    return {
        "trip_safety_score":    trip_safety_score,
        "risk_label":           risk_label,
        "risk_category":        risk_category,
        "speed_score":          round(speed_score, 2),
        "braking_score":        round(braking_score, 2),
        "acceleration_score":   round(acceleration_score, 2),
        "speed_risk":           speed_risk_flag,
        "braking_risk":         braking_risk_flag,
        "acceleration_risk":    accel_risk_flag,
        "total_harsh_events":   total_harsh,
        "harsh_events_per_minute": harsh_pm,
        "is_high_risk":         is_high_risk,
        "speed_difference":     round(spd_diff, 2),
        "contributing_factors": factors,
    }


def get_risk_label(score: float):
    if score >= 70:  return "Low Risk", "Low"
    if score >= 40:  return "Moderate Risk", "Moderate"
    return "High Risk", "High"
