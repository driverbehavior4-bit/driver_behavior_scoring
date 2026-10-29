"""backend/app/utils/driver_analytics.py"""
import numpy as np
from typing import List, Any


def _get_val(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def calculate_driver_overall_score(scores_list) -> dict:
    """
    Compute driver-level metrics from a list of Score objects or MongoDB dicts.
    Sorted by created_at (chronological). Recency-weighted average.
    """
    if not scores_list:
        return {"overall_score": 0.0, "risk_category": "No Data",
                "is_high_risk": False, "trip_count": 0,
                "trend": "stable", "avg_score": 0.0, "latest_score": 0.0}

    sorted_scores = sorted(scores_list, key=lambda s: str(_get_val(s, "created_at", "")))
    vals = np.array([float(_get_val(s, "trip_safety_score", 0.0)) for s in sorted_scores], dtype=float)
    n = len(vals)

    weights = np.arange(1, n+1, dtype=float)
    weights /= weights.sum()
    overall = float(round((vals * weights).sum(), 2))
    avg     = float(round(vals.mean(), 2))
    latest  = float(round(vals[-1], 2))

    if overall >= 70:   cat = "Low"
    elif overall >= 40: cat = "Moderate"
    else:               cat = "High"

    last5_avg = float(vals[-5:].mean()) if n >= 5 else avg
    is_high   = overall < 40 or (overall < 55 and last5_avg < 45)

    mid = max(1, n//2)
    first_half  = float(vals[:mid].mean())
    second_half = float(vals[mid:].mean())
    if abs(second_half - first_half) < 3:   trend = "stable"
    elif second_half > first_half:           trend = "improving"
    else:                                    trend = "declining"

    return {"overall_score": overall, "risk_category": cat, "is_high_risk": is_high,
            "trip_count": n, "trend": trend, "avg_score": avg, "latest_score": latest}
