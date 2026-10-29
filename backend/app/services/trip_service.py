"""backend/app/services/trip_service.py"""
import uuid
from datetime import date as date_type
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models import Driver, Trip, Score
from app.schemas import TripCreate
from app.utils.scoring import calculate_trip_score


def _new_trip_id(db: Session) -> str:
    while True:
        tid = "T-" + uuid.uuid4().hex[:8].upper()
        if not db.query(Trip).filter(Trip.trip_id == tid).first():
            return tid


def process_new_trip(db: Session, data: TripCreate) -> dict:
    driver = db.query(Driver).filter(Driver.driver_id == data.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{data.driver_id}' not found.")

    avg = data.average_speed or 0.0
    mx  = data.max_speed or 0.0
    if mx > 0 and avg > mx:
        raise HTTPException(status_code=422, detail="average_speed cannot exceed max_speed.")

    trip_id = data.trip_id or _new_trip_id(db)
    if data.trip_id and db.query(Trip).filter(Trip.trip_id == data.trip_id).first():
        raise HTTPException(status_code=409, detail=f"Trip '{data.trip_id}' already exists.")

    trip = Trip(trip_id=trip_id, driver_id=data.driver_id,
                trip_date=data.trip_date or date_type.today(),
                average_speed=avg, max_speed=mx,
                harsh_braking=data.harsh_braking or 0,
                harsh_acceleration=data.harsh_acceleration or 0,
                trip_duration=max(data.trip_duration or 1.0, 0.1),
                distance=data.distance, idle_time=data.idle_time)
    db.add(trip)

    sd = calculate_trip_score(trip.max_speed, trip.harsh_braking,
                              trip.harsh_acceleration, trip.trip_duration, trip.average_speed)
    score = Score(trip_id=trip_id, driver_id=data.driver_id,
                  trip_safety_score=sd["trip_safety_score"],
                  risk_label=sd["risk_label"], risk_category=sd["risk_category"],
                  speed_score=sd["speed_score"], braking_score=sd["braking_score"],
                  acceleration_score=sd["acceleration_score"],
                  speed_risk=sd["speed_risk"], braking_risk=sd["braking_risk"],
                  acceleration_risk=sd["acceleration_risk"],
                  total_harsh_events=sd["total_harsh_events"],
                  harsh_events_per_minute=sd["harsh_events_per_minute"],
                  is_high_risk=sd["is_high_risk"])
    db.add(score)

    try:
        db.commit()
        db.refresh(trip); db.refresh(score)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"DB error: {e.orig}")

    return {"trip": trip, "score": score, "score_data": sd}
