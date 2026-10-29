"""
All backend routes with dual MongoDB and SQL support.
Defaults to MongoDB (DATABASE_TYPE=mongodb in .env).
"""
import os
from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.database.connection import get_db
from app.models import User, Driver, Trip, Score, CoachingAction
from app.schemas import (LoginRequest, Token, DriverCreate, DriverUpdate, DriverResponse,
                         DriverList, TripCreate, TripResponse, TripList, ScoreResponse,
                         DriverScoreSummary, CoachingCreate, CoachingUpdate, CoachingResponse,
                         DashboardStats, FleetAnalytics, HighRiskDriver, DriverTrend, DriverTrendPoint)
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user
from app.utils.driver_analytics import calculate_driver_overall_score
from app.services.trip_service import process_new_trip

# MongoDB DAL
from app.database.mongodb import (
    mongo_get_user, mongo_get_drivers, mongo_get_driver, mongo_create_driver, mongo_update_driver,
    mongo_get_trips, mongo_get_trip, mongo_get_driver_trips, mongo_process_new_trip,
    mongo_get_trip_score, mongo_get_driver_score_summary,
    mongo_dashboard_stats, mongo_fleet_analytics, mongo_high_risk_drivers, mongo_driver_trend,
    mongo_get_coaching, mongo_create_coaching, mongo_update_coaching, mongo_get_driver_coaching
)

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "mongodb").lower()

# ─────────────────────────────────────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────────────────────────────────────
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

def _auth_sql(db, username, password):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled.")
    return user

@auth_router.post("/login", response_model=Token, summary="Login with JSON body")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if DATABASE_TYPE == "mongodb":
        user = mongo_get_user(req.username)
        if not user or not verify_password(req.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password",
                                headers={"WWW-Authenticate": "Bearer"})
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account disabled.")
        token = create_access_token({"sub": user["username"], "role": user["role"]})
        return Token(access_token=token, token_type="bearer", role=user["role"], username=user["username"])

    user  = _auth_sql(db, req.username, req.password)
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, token_type="bearer", role=user.role, username=user.username)

@auth_router.post("/token", response_model=Token, summary="OAuth2 form login (Swagger)")
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if DATABASE_TYPE == "mongodb":
        user = mongo_get_user(form.username)
        if not user or not verify_password(form.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password",
                                headers={"WWW-Authenticate": "Bearer"})
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account disabled.")
        token = create_access_token({"sub": user["username"], "role": user["role"]})
        return Token(access_token=token, token_type="bearer", role=user["role"], username=user["username"])

    user  = _auth_sql(db, form.username, form.password)
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, token_type="bearer", role=user.role, username=user.username)


# ─────────────────────────────────────────────────────────────────────────────
#  DRIVERS
# ─────────────────────────────────────────────────────────────────────────────
drivers_router = APIRouter(tags=["Drivers"])

def _driver_with_score_sql(driver, db):
    scores = db.query(Score).filter(Score.driver_id == driver.driver_id).all()
    summary = calculate_driver_overall_score(scores)
    d = DriverResponse.model_validate(driver)
    d.overall_score  = summary["overall_score"]
    d.risk_category  = summary["risk_category"]
    d.is_high_risk   = summary["is_high_risk"]
    d.trip_count     = summary["trip_count"]
    return d

@drivers_router.get("/drivers", summary="List all drivers")
def list_drivers(db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_get_drivers()

    drivers = db.query(Driver).order_by(Driver.driver_id).all()
    return [_driver_with_score_sql(d, db) for d in drivers]

@drivers_router.get("/drivers/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        d = mongo_get_driver(driver_id)
        if not d:
            raise HTTPException(404, f"Driver '{driver_id}' not found.")
        return d

    d = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not d:
        raise HTTPException(404, f"Driver '{driver_id}' not found.")
    return _driver_with_score_sql(d, db)

@drivers_router.post("/drivers", response_model=DriverResponse, status_code=201)
def create_driver(data: DriverCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        try:
            return mongo_create_driver(data.model_dump())
        except ValueError as e:
            raise HTTPException(409, str(e))

    if db.query(Driver).filter(Driver.driver_id == data.driver_id).first():
        raise HTTPException(409, f"Driver '{data.driver_id}' already exists.")
    d = Driver(**data.model_dump())
    db.add(d); db.commit(); db.refresh(d)
    return _driver_with_score_sql(d, db)

@drivers_router.put("/drivers/{driver_id}", response_model=DriverResponse)
def update_driver(driver_id: str, data: DriverUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        d = mongo_update_driver(driver_id, data.model_dump(exclude_none=True))
        if not d:
            raise HTTPException(404, f"Driver '{driver_id}' not found.")
        return d

    d = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not d:
        raise HTTPException(404, f"Driver '{driver_id}' not found.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(d, k, v)
    db.commit(); db.refresh(d)
    return _driver_with_score_sql(d, db)


# ─────────────────────────────────────────────────────────────────────────────
#  TRIPS
# ─────────────────────────────────────────────────────────────────────────────
trips_router = APIRouter(tags=["Trips"])

@trips_router.get("/trips", response_model=TripList)
def list_trips(skip: int = 0, limit: int = Query(100, le=1000),
               driver_id: Optional[str] = None,
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_get_trips(skip=skip, limit=limit, driver_id=driver_id)

    q = db.query(Trip)
    if driver_id: q = q.filter(Trip.driver_id == driver_id)
    total = q.count()
    trips = q.order_by(Trip.created_at.desc()).offset(skip).limit(limit).all()
    return TripList(total=total, trips=trips)

@trips_router.post("/trips", status_code=201)
def create_trip(data: TripCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        try:
            return mongo_process_new_trip(data.model_dump())
        except KeyError as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            msg = str(e)
            if "not found" in msg:
                raise HTTPException(404, msg)
            raise HTTPException(422, msg)

    res  = process_new_trip(db, data)
    trip = res["trip"]; score = res["score"]; sd = res["score_data"]
    return {"message":"Trip processed and scored successfully.",
            "trip_id":trip.trip_id, "driver_id":trip.driver_id,
            "trip_date":str(trip.trip_date), "average_speed":trip.average_speed,
            "max_speed":trip.max_speed, "harsh_braking":trip.harsh_braking,
            "harsh_acceleration":trip.harsh_acceleration, "trip_duration":trip.trip_duration,
            "trip_safety_score":score.trip_safety_score, "risk_label":score.risk_label,
            "risk_category":score.risk_category, "speed_score":score.speed_score,
            "braking_score":score.braking_score, "acceleration_score":score.acceleration_score,
            "is_high_risk":score.is_high_risk, "contributing_factors":sd.get("contributing_factors",[])}

@trips_router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        t = mongo_get_trip(trip_id)
        if not t:
            raise HTTPException(404, f"Trip '{trip_id}' not found.")
        return t

    t = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not t:
        raise HTTPException(404, f"Trip '{trip_id}' not found.")
    return t

@trips_router.get("/drivers/{driver_id}/trips", response_model=TripList)
def get_driver_trips(driver_id: str, skip: int = 0, limit: int = Query(100, le=1000),
                     db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_get_driver_trips(driver_id=driver_id, skip=skip, limit=limit)

    q = db.query(Trip).filter(Trip.driver_id == driver_id)
    total = q.count()
    trips = q.order_by(Trip.trip_date.desc()).offset(skip).limit(limit).all()
    return TripList(total=total, trips=trips)


# ─────────────────────────────────────────────────────────────────────────────
#  SCORES
# ─────────────────────────────────────────────────────────────────────────────
scores_router = APIRouter(prefix="/scores", tags=["Scores"])

@scores_router.get("/trip/{trip_id}", response_model=ScoreResponse)
def get_trip_score(trip_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        s = mongo_get_trip_score(trip_id)
        if not s:
            raise HTTPException(404, f"Score for trip '{trip_id}' not found.")
        return s

    s = db.query(Score).filter(Score.trip_id == trip_id).first()
    if not s:
        raise HTTPException(404, f"Score for trip '{trip_id}' not found.")
    return s

@scores_router.get("/driver/{driver_id}", response_model=DriverScoreSummary)
def get_driver_score(driver_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        d = mongo_get_driver_score_summary(driver_id)
        if not d:
            raise HTTPException(404, f"Driver '{driver_id}' not found.")
        return d

    d = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not d:
        raise HTTPException(404, f"Driver '{driver_id}' not found.")
    scores  = db.query(Score).filter(Score.driver_id == driver_id).order_by(Score.created_at).all()
    summary = calculate_driver_overall_score(scores)
    return DriverScoreSummary(driver_id=driver_id, driver_name=d.name, **summary)


# ─────────────────────────────────────────────────────────────────────────────
#  ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])

@analytics_router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_dashboard_stats()

    total_drivers = db.query(Driver).count()
    total_trips   = db.query(Trip).count()
    trips_today   = db.query(Trip).filter(func.date(Trip.created_at) == date.today()).count()
    pending_coaching = db.query(CoachingAction).filter(
        CoachingAction.status.in_(["pending","in_progress"])).count()

    driver_ids = [r.driver_id for r in db.query(Driver.driver_id).all()]
    high_risk = moderate = low_risk = 0
    total_score_sum = 0.0; drivers_with_scores = 0
    for did in driver_ids:
        scores = db.query(Score).filter(Score.driver_id == did).all()
        if not scores: continue
        drivers_with_scores += 1
        summary = calculate_driver_overall_score(scores)
        total_score_sum += summary["overall_score"]
        cat = summary["risk_category"]
        if cat == "High": high_risk += 1
        elif cat == "Moderate": moderate += 1
        else: low_risk += 1

    avg_fleet = round(total_score_sum / drivers_with_scores, 2) if drivers_with_scores else 0.0
    return DashboardStats(total_drivers=total_drivers, total_trips=total_trips,
                          avg_fleet_score=avg_fleet, high_risk_drivers=high_risk,
                          moderate_risk_drivers=moderate, low_risk_drivers=low_risk,
                          trips_today=trips_today, pending_coaching_actions=pending_coaching)

@analytics_router.get("/fleet", response_model=FleetAnalytics)
def fleet_analytics(db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_fleet_analytics()

    scores = db.query(Score).all()
    if not scores:
        return FleetAnalytics(avg_score=0.0,score_distribution={},avg_speed_score=0.0,
                              avg_braking_score=0.0,avg_acceleration_score=0.0,
                              total_harsh_events=0,high_risk_count=0,drivers_with_trips=0)
    n   = len(scores)
    avg = round(sum(s.trip_safety_score for s in scores)/n, 2)
    avs = round(sum(s.speed_score or 0 for s in scores)/n, 2)
    avb = round(sum(s.braking_score or 0 for s in scores)/n, 2)
    ava = round(sum(s.acceleration_score or 0 for s in scores)/n, 2)
    thr = sum(s.total_harsh_events or 0 for s in scores)
    hrc = sum(1 for s in scores if s.is_high_risk)
    dist = {"Low Risk":0,"Moderate Risk":0,"High Risk":0}
    for s in scores:
        if s.risk_label in dist: dist[s.risk_label] += 1
    dwt = db.query(Score.driver_id).distinct().count()

    buckets = {f"{i*10}-{(i+1)*10}": 0 for i in range(10)}
    for s in scores:
        b = min(int(s.trip_safety_score // 10), 9)
        buckets[f"{b*10}-{(b+1)*10}"] += 1

    from sqlalchemy import func as F
    harsh_rows = (db.query(Score.driver_id, F.sum(Score.total_harsh_events).label("total"))
                  .group_by(Score.driver_id).order_by(F.sum(Score.total_harsh_events).desc())
                  .limit(10).all())
    top_harsh = []
    for row in harsh_rows:
        drv = db.query(Driver).filter(Driver.driver_id == row.driver_id).first()
        top_harsh.append({"driver_id":row.driver_id,
                           "name": drv.name if drv else row.driver_id,
                           "total_harsh_events": int(row.total)})

    from datetime import timedelta
    today = date.today()
    daily = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        cnt = db.query(Trip).filter(func.date(Trip.trip_date) == d).count()
        daily.append({"date": d.isoformat(), "count": cnt})

    return FleetAnalytics(avg_score=avg, score_distribution=dist,
                          avg_speed_score=avs, avg_braking_score=avb,
                          avg_acceleration_score=ava, total_harsh_events=thr,
                          high_risk_count=hrc, drivers_with_trips=dwt,
                          score_buckets=buckets, top_harsh_drivers=top_harsh,
                          daily_trips=daily)

@analytics_router.get("/high-risk-drivers", response_model=List[HighRiskDriver])
def high_risk_drivers(limit: int = Query(50, le=200), db: Session = Depends(get_db),
                      _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_high_risk_drivers(limit=limit)

    results = []
    for drv in db.query(Driver).all():
        scores  = db.query(Score).filter(Score.driver_id == drv.driver_id).order_by(Score.created_at).all()
        if not scores: continue
        summary = calculate_driver_overall_score(scores)
        if summary["risk_category"] != "High": continue
        latest_coaching = (db.query(CoachingAction)
                           .filter(CoachingAction.driver_id == drv.driver_id)
                           .order_by(CoachingAction.created_at.desc()).first())
        coaching_status = latest_coaching.status if latest_coaching else None

        factors = []
        high_spd = sum(1 for s in scores if (s.speed_risk or False))
        high_brk = sum(1 for s in scores if (s.braking_risk or False))
        high_acc = sum(1 for s in scores if (s.acceleration_risk or False))
        n = len(scores)
        if high_spd/n > 0.2: factors.append(f"Excessive speed ({high_spd}/{n} trips)")
        if high_brk/n > 0.2: factors.append(f"Harsh braking ({high_brk}/{n} trips)")
        if high_acc/n > 0.2: factors.append(f"Harsh acceleration ({high_acc}/{n} trips)")
        if not factors: factors.append("Combined risk factors")

        results.append(HighRiskDriver(
            driver_id=drv.driver_id, driver_name=drv.name,
            overall_score=summary["overall_score"], risk_category=summary["risk_category"],
            total_trips=summary["trip_count"], latest_score=summary["latest_score"],
            trend=summary["trend"], coaching_status=coaching_status, risk_factors=factors))

    results.sort(key=lambda x: x.overall_score)
    return results[:limit]

@analytics_router.get("/driver/{driver_id}/trend", response_model=DriverTrend)
def driver_trend(driver_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        tr = mongo_driver_trend(driver_id)
        if not tr:
            raise HTTPException(404, f"Driver '{driver_id}' not found.")
        return tr

    drv = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not drv: raise HTTPException(404, f"Driver '{driver_id}' not found.")
    scores  = db.query(Score).filter(Score.driver_id == driver_id).order_by(Score.created_at).all()
    summary = calculate_driver_overall_score(scores)
    trend_data = []
    for s in scores:
        td = None
        if s.trip and s.trip.trip_date:
            td = str(s.trip.trip_date)
        elif s.created_at:
            td = str(s.created_at.date())
        trend_data.append(DriverTrendPoint(trip_id=s.trip_id, trip_date=td,
                                           trip_safety_score=s.trip_safety_score,
                                           risk_category=s.risk_category))
    return DriverTrend(driver_id=driver_id, driver_name=drv.name,
                       overall_score=summary["overall_score"],
                       risk_category=summary["risk_category"],
                       trend=summary["trend"], trip_count=summary["trip_count"],
                       trend_data=trend_data)


# ─────────────────────────────────────────────────────────────────────────────
#  COACHING
# ─────────────────────────────────────────────────────────────────────────────
coaching_router = APIRouter(prefix="/coaching", tags=["Coaching"])

@coaching_router.get("", response_model=List[CoachingResponse])
def list_coaching(db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_get_coaching()

    return db.query(CoachingAction).order_by(CoachingAction.created_at.desc()).all()

@coaching_router.post("", response_model=CoachingResponse, status_code=201)
def create_coaching(data: CoachingCreate, db: Session = Depends(get_db),
                    user: dict = Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        try:
            return mongo_create_coaching(data.model_dump(), user)
        except ValueError as e:
            raise HTTPException(404, str(e))

    if not db.query(Driver).filter(Driver.driver_id == data.driver_id).first():
        raise HTTPException(404, f"Driver '{data.driver_id}' not found.")
    u = db.query(User).filter(User.username == user["sub"]).first()
    rf = json.dumps(data.risk_factors) if isinstance(data.risk_factors, list) else (data.risk_factors or "")
    ca = CoachingAction(driver_id=data.driver_id, created_by=u.id if u else 1,
                        reason=data.reason, risk_factors=rf,
                        coaching_notes=data.coaching_notes, action_taken=data.action_taken,
                        status=data.status, follow_up_date=data.follow_up_date)
    db.add(ca); db.commit(); db.refresh(ca)
    return ca

@coaching_router.put("/{action_id}", response_model=CoachingResponse)
def update_coaching(action_id: int, data: CoachingUpdate,
                    db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        ca = mongo_update_coaching(action_id, data.model_dump(exclude_none=True))
        if not ca:
            raise HTTPException(404, "Coaching action not found.")
        return ca

    ca = db.query(CoachingAction).filter(CoachingAction.id == action_id).first()
    if not ca: raise HTTPException(404, "Coaching action not found.")
    for k, v in data.model_dump(exclude_none=True).items():
        if k == "risk_factors" and isinstance(v, list):
            v = json.dumps(v)
        setattr(ca, k, v)
    ca.updated_at = datetime.utcnow()
    db.commit(); db.refresh(ca)
    return ca

@coaching_router.get("/driver/{driver_id}", response_model=List[CoachingResponse])
def get_driver_coaching(driver_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if DATABASE_TYPE == "mongodb":
        return mongo_get_driver_coaching(driver_id)

    return db.query(CoachingAction).filter(CoachingAction.driver_id == driver_id).order_by(CoachingAction.created_at.desc()).all()
