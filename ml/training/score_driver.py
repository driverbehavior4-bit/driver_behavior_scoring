"""
ml/training/score_driver.py
Driver-level scoring from trip history.
"""
import numpy as np


def calculate_driver_score(scores_list: list) -> dict:
    """
    Compute driver overall score from list of trip_safety_score floats.
    scores_list should be ordered chronologically (oldest first).
    """
    if not scores_list:
        return {"overall_score": 0.0, "risk_category": "No Data",
                "is_high_risk": False, "trip_count": 0,
                "trend": "stable", "avg_score": 0.0, "latest_score": 0.0}

    n = len(scores_list)
    # Recency weights: recent trips weighted more (linear)
    weights = np.arange(1, n+1, dtype=float)
    weights /= weights.sum()
    arr = np.array(scores_list, dtype=float)
    overall = float(round((arr * weights).sum(), 2))
    avg     = float(round(arr.mean(), 2))
    latest  = float(arr[-1])

    # Risk category
    if overall >= 70:
        cat = "Low Risk"
    elif overall >= 40:
        cat = "Moderate Risk"
    else:
        cat = "High Risk"

    # High-risk flag
    last5_avg = float(arr[-5:].mean()) if n >= 5 else avg
    is_high   = overall < 40 or (overall < 55 and last5_avg < 45)

    # Trend (compare first half avg vs second half avg)
    mid  = max(1, n // 2)
    first_half  = float(arr[:mid].mean())
    second_half = float(arr[mid:].mean())
    if abs(second_half - first_half) < 3:
        trend = "stable"
    elif second_half > first_half:
        trend = "improving"
    else:
        trend = "declining"

    return {"overall_score": overall, "risk_category": cat, "is_high_risk": is_high,
            "trip_count": n, "trend": trend, "avg_score": avg,
            "latest_score": round(latest, 2)}


def get_risk_factors(trip_records: list) -> list:
    """
    Analyse list of trip dicts and return top risk factor strings.
    Each record may have: max_speed, harsh_braking, harsh_acceleration.
    """
    if not trip_records:
        return ["Insufficient trip data"]

    speeding    = sum(1 for r in trip_records if r.get("max_speed", 0) > 100)
    braking     = sum(1 for r in trip_records if r.get("harsh_braking", 0) >= 4)
    accel       = sum(1 for r in trip_records if r.get("harsh_acceleration", 0) >= 4)
    n = len(trip_records)

    factors = []
    if speeding / n > 0.25:
        factors.append(f"Excessive speed in {speeding}/{n} trips")
    if braking / n > 0.25:
        factors.append(f"Frequent harsh braking in {braking}/{n} trips")
    if accel / n > 0.25:
        factors.append(f"Frequent harsh acceleration in {accel}/{n} trips")
    if not factors:
        factors.append("No significant risk factors identified")
    return factors
