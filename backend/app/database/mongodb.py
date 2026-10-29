"""
backend/app/database/mongodb.py — MongoDB database driver and repository layer.
Supports both local MongoDB (mongodb://localhost:27017), MongoDB Atlas (mongodb+srv://...),
and in-memory mongomock fallback for standalone testing if mongod is not yet running.
"""
import os
import csv
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

def _get_configured_uri():
    uri = os.getenv("MONGODB_URI")
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("mongodb://") or db_url.startswith("mongodb+srv://"):
        return db_url
    if uri:
        return uri
    return "mongodb://localhost:27017"

MONGODB_URI = _get_configured_uri()
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "driver_safety")

_client = None
_db = None
_is_mock = False


def get_mongo_client():
    global _client, _db, _is_mock, MONGODB_URI
    if _client is not None:
        return _client

    MONGODB_URI = _get_configured_uri()
    try:
        from pymongo import MongoClient
        kwargs = {"serverSelectionTimeoutMS": 3000}
        if "mongodb+srv://" in MONGODB_URI or "ssl=true" in MONGODB_URI.lower():
            try:
                import certifi
                kwargs["tlsCAFile"] = certifi.where()
            except ImportError:
                pass

        client = MongoClient(MONGODB_URI, **kwargs)
        # Verify connection
        client.admin.command('ping')
        _client = client
        _db = _client[MONGODB_DB_NAME]
        _is_mock = False
        print(f"[MongoDB] Successfully connected to MongoDB: {MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI}")
    except Exception as e:
        err_msg = str(e)
        print(f"[MongoDB] Could not connect to remote MongoDB ({err_msg[:120]}...)")
        if "SSL" in err_msg or "TLS" in err_msg:
            print("[MongoDB Note] If using MongoDB Atlas, make sure your IP is whitelisted in MongoDB Atlas:")
            print("               Go to Atlas -> Network Access -> Add IP Address -> 'Allow Access from Anywhere' (0.0.0.0/0)")
        print("[MongoDB] Initializing in-memory MongoMock database so the application runs seamlessly.")
        import mongomock
        _client = mongomock.MongoClient()
        _db = _client[MONGODB_DB_NAME]
        _is_mock = True

    _setup_indexes(_db)
    return _client


def get_mongo_db():
    global _db
    if _db is None:
        get_mongo_client()
    return _db


def _setup_indexes(db):
    try:
        db.users.create_index("username", unique=True)
        db.users.create_index("email", unique=True)
        db.drivers.create_index("driver_id", unique=True)
        db.trips.create_index("trip_id", unique=True)
        db.trips.create_index("driver_id")
        db.scores.create_index("trip_id", unique=True)
        db.scores.create_index("driver_id")
        db.coaching_actions.create_index("id", unique=True)
        db.coaching_actions.create_index("driver_id")
    except Exception as e:
        print(f"[MongoDB] Index setup note: {e}")


def _clean_doc(doc: Optional[dict]) -> Optional[dict]:
    """Removes MongoDB _id and ensures JSON serializability."""
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def _clean_docs(cursor) -> List[dict]:
    return [_clean_doc(d) for d in cursor]


# ── SEEDING ──────────────────────────────────────────────────────────────────

def seed_mongo_users(db):
    from app.utils.security import hash_password
    default_users = [
        {"id": 1, "username": "admin", "email": "admin@fleet.com", "password": "admin123", "role": "admin"},
        {"id": 2, "username": "fleet_manager", "email": "manager@fleet.com", "password": "fleet123", "role": "fleet_manager"},
    ]
    for u in default_users:
        if not db.users.find_one({"username": u["username"]}):
            db.users.insert_one({
                "id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "hashed_password": hash_password(u["password"]),
                "role": u["role"],
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
            })
            print(f"[MongoDB] Seeded user: {u['username']} ({u['role']})")


def seed_mongo_from_csv(db, csv_path: str):
    if not os.path.exists(csv_path):
        print(f"[MongoDB] CSV file not found: {csv_path}")
        return

    if db.trips.count_documents({}) > 0:
        print(f"[MongoDB] Trips already present in MongoDB ({db.trips.count_documents({})}), skipping CSV seed.")
        return

    from app.utils.scoring import calculate_trip_score

    print(f"[MongoDB] Seeding database from CSV: {csv_path} ...")
    drivers_seen = set()
    driver_docs = []
    trip_docs = []
    score_docs = []

    driver_id_seq = 1
    trip_id_seq = 1

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            did = row.get("driver_id", "").strip()
            tid = row.get("trip_id", "").strip()
            dname = row.get("driver_name", f"Driver {did}").strip()
            if not did or not tid:
                continue

            if did not in drivers_seen:
                drivers_seen.add(did)
                driver_docs.append({
                    "id": driver_id_seq,
                    "driver_id": did,
                    "name": dname,
                    "email": f"{did.lower()}@fleet.com",
                    "phone": f"+1-555-{1000 + driver_id_seq}",
                    "license_number": f"LIC-{did}",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                })
                driver_id_seq += 1

            def _f(k, d=0.0):
                try: return float(row.get(k, d) or d)
                except: return d
            def _i(k, d=0):
                try: return int(float(row.get(k, d) or d))
                except: return d

            avg_spd = _f("average_speed")
            max_spd = _f("max_speed")
            hb = _i("harsh_braking")
            ha = _i("harsh_acceleration")
            dur = max(_f("trip_duration", 1.0), 0.1)
            dist = _f("distance") or None
            idle = _f("idle_time") or None
            tdate = row.get("trip_date", date.today().isoformat())

            sd = calculate_trip_score(max_spd, hb, ha, dur, avg_spd)

            trip_docs.append({
                "id": trip_id_seq,
                "trip_id": tid,
                "driver_id": did,
                "trip_date": tdate,
                "average_speed": avg_spd,
                "max_speed": max_spd,
                "harsh_braking": hb,
                "harsh_acceleration": ha,
                "trip_duration": dur,
                "distance": dist,
                "idle_time": idle,
                "created_at": datetime.utcnow().isoformat(),
            })

            score_docs.append({
                "id": trip_id_seq,
                "trip_id": tid,
                "driver_id": did,
                "trip_safety_score": sd["trip_safety_score"],
                "risk_label": sd["risk_label"],
                "risk_category": sd["risk_category"],
                "speed_score": sd["speed_score"],
                "braking_score": sd["braking_score"],
                "acceleration_score": sd["acceleration_score"],
                "speed_risk": sd["speed_risk"],
                "braking_risk": sd["braking_risk"],
                "acceleration_risk": sd["acceleration_risk"],
                "total_harsh_events": sd["total_harsh_events"],
                "harsh_events_per_minute": sd["harsh_events_per_minute"],
                "is_high_risk": sd["is_high_risk"],
                "created_at": datetime.utcnow().isoformat(),
            })
            trip_id_seq += 1

    if driver_docs:
        db.drivers.insert_many(driver_docs)
    if trip_docs:
        db.trips.insert_many(trip_docs)
    if score_docs:
        db.scores.insert_many(score_docs)

    print(f"[MongoDB] Seed completed: {len(driver_docs)} drivers, {len(trip_docs)} trips, {len(score_docs)} scores.")


def initialize_mongodb():
    db = get_mongo_db()
    seed_mongo_users(db)

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.normpath(os.path.join(here, "..", "..", "..", "data", "raw", "driving_data.csv")),
        os.path.normpath(os.path.join(here, "..", "..", "data", "raw", "driving_data.csv")),
    ]
    for p in candidates:
        if os.path.exists(p):
            seed_mongo_from_csv(db, p)
            break


# ── DATA ACCESS HELPERS ──────────────────────────────────────────────────────

# Auth
def mongo_get_user(username: str) -> Optional[dict]:
    db = get_mongo_db()
    return _clean_doc(db.users.find_one({"username": username}))


# Drivers
def mongo_get_drivers() -> List[dict]:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score
    drivers = _clean_docs(db.drivers.find().sort("driver_id", 1))
    for d in drivers:
        scores = list(db.scores.find({"driver_id": d["driver_id"]}))
        summary = calculate_driver_overall_score(scores)
        d["overall_score"] = summary["overall_score"]
        d["risk_category"] = summary["risk_category"]
        d["is_high_risk"] = summary["is_high_risk"]
        d["trip_count"] = summary["trip_count"]
    return drivers


def mongo_get_driver(driver_id: str) -> Optional[dict]:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score
    d = _clean_doc(db.drivers.find_one({"driver_id": driver_id}))
    if not d:
        return None
    scores = list(db.scores.find({"driver_id": driver_id}))
    summary = calculate_driver_overall_score(scores)
    d["overall_score"] = summary["overall_score"]
    d["risk_category"] = summary["risk_category"]
    d["is_high_risk"] = summary["is_high_risk"]
    d["trip_count"] = summary["trip_count"]
    return d


def mongo_create_driver(data: dict) -> dict:
    db = get_mongo_db()
    existing = db.drivers.find_one({"driver_id": data["driver_id"]})
    if existing:
        raise ValueError(f"Driver '{data['driver_id']}' already exists.")

    count = db.drivers.count_documents({})
    now = datetime.utcnow().isoformat()
    doc = {
        "id": count + 1,
        "driver_id": data["driver_id"],
        "name": data["name"],
        "email": data.get("email"),
        "phone": data.get("phone"),
        "license_number": data.get("license_number"),
        "created_at": now,
        "updated_at": now,
        "overall_score": 0.0,
        "risk_category": "No Data",
        "is_high_risk": False,
        "trip_count": 0,
    }
    db.drivers.insert_one(dict(doc))
    return _clean_doc(doc)


def mongo_update_driver(driver_id: str, data: dict) -> Optional[dict]:
    db = get_mongo_db()
    updates = {k: v for k, v in data.items() if v is not None}
    updates["updated_at"] = datetime.utcnow().isoformat()
    db.drivers.update_one({"driver_id": driver_id}, {"$set": updates})
    return mongo_get_driver(driver_id)


# Trips & Scoring
def mongo_get_trips(skip: int = 0, limit: int = 100, driver_id: Optional[str] = None) -> dict:
    db = get_mongo_db()
    q = {"driver_id": driver_id} if driver_id else {}
    total = db.trips.count_documents(q)
    trips = _clean_docs(db.trips.find(q).sort("created_at", -1).skip(skip).limit(limit))
    return {"total": total, "trips": trips}


def mongo_get_trip(trip_id: str) -> Optional[dict]:
    db = get_mongo_db()
    return _clean_doc(db.trips.find_one({"trip_id": trip_id}))


def mongo_get_driver_trips(driver_id: str, skip: int = 0, limit: int = 100) -> dict:
    return mongo_get_trips(skip=skip, limit=limit, driver_id=driver_id)


def mongo_process_new_trip(data: dict) -> dict:
    db = get_mongo_db()
    from app.utils.scoring import calculate_trip_score

    driver = db.drivers.find_one({"driver_id": data["driver_id"]})
    if not driver:
        raise ValueError(f"Driver '{data['driver_id']}' not found.")

    avg = float(data.get("average_speed", 0.0))
    mx = float(data.get("max_speed", 0.0))
    if mx > 0 and avg > mx:
        raise ValueError("average_speed cannot exceed max_speed.")

    trip_id = data.get("trip_id")
    if not trip_id:
        while True:
            candidate = "T-" + uuid.uuid4().hex[:8].upper()
            if not db.trips.find_one({"trip_id": candidate}):
                trip_id = candidate
                break
    else:
        if db.trips.find_one({"trip_id": trip_id}):
            raise KeyError(f"Trip '{trip_id}' already exists.")

    count = db.trips.count_documents({})
    now = datetime.utcnow().isoformat()
    tdate = data.get("trip_date") or date.today().isoformat()
    if isinstance(tdate, (date, datetime)):
        tdate = tdate.isoformat()

    dur = max(float(data.get("trip_duration", 1.0)), 0.1)
    hb = int(data.get("harsh_braking", 0))
    ha = int(data.get("harsh_acceleration", 0))

    trip_doc = {
        "id": count + 1,
        "trip_id": trip_id,
        "driver_id": data["driver_id"],
        "trip_date": tdate,
        "average_speed": avg,
        "max_speed": mx,
        "harsh_braking": hb,
        "harsh_acceleration": ha,
        "trip_duration": dur,
        "distance": data.get("distance"),
        "idle_time": data.get("idle_time"),
        "created_at": now,
    }
    db.trips.insert_one(dict(trip_doc))

    sd = calculate_trip_score(mx, hb, ha, dur, avg)

    score_doc = {
        "id": count + 1,
        "trip_id": trip_id,
        "driver_id": data["driver_id"],
        "trip_safety_score": sd["trip_safety_score"],
        "risk_label": sd["risk_label"],
        "risk_category": sd["risk_category"],
        "speed_score": sd["speed_score"],
        "braking_score": sd["braking_score"],
        "acceleration_score": sd["acceleration_score"],
        "speed_risk": sd["speed_risk"],
        "braking_risk": sd["braking_risk"],
        "acceleration_risk": sd["acceleration_risk"],
        "total_harsh_events": sd["total_harsh_events"],
        "harsh_events_per_minute": sd["harsh_events_per_minute"],
        "is_high_risk": sd["is_high_risk"],
        "created_at": now,
    }
    db.scores.insert_one(dict(score_doc))

    return {
        "message": "Trip processed and scored successfully.",
        "trip_id": trip_id,
        "driver_id": data["driver_id"],
        "trip_date": str(tdate),
        "average_speed": avg,
        "max_speed": mx,
        "harsh_braking": hb,
        "harsh_acceleration": ha,
        "trip_duration": dur,
        "trip_safety_score": sd["trip_safety_score"],
        "risk_label": sd["risk_label"],
        "risk_category": sd["risk_category"],
        "speed_score": sd["speed_score"],
        "braking_score": sd["braking_score"],
        "acceleration_score": sd["acceleration_score"],
        "is_high_risk": sd["is_high_risk"],
        "contributing_factors": sd.get("contributing_factors", []),
    }


# Scores
def mongo_get_trip_score(trip_id: str) -> Optional[dict]:
    db = get_mongo_db()
    return _clean_doc(db.scores.find_one({"trip_id": trip_id}))


def mongo_get_driver_score_summary(driver_id: str) -> Optional[dict]:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score
    drv = db.drivers.find_one({"driver_id": driver_id})
    if not drv:
        return None
    scores = list(db.scores.find({"driver_id": driver_id}))
    summary = calculate_driver_overall_score(scores)
    return {
        "driver_id": driver_id,
        "driver_name": drv.get("name", driver_id),
        **summary,
    }


# Analytics
def mongo_dashboard_stats() -> dict:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score

    total_drivers = db.drivers.count_documents({})
    total_trips = db.trips.count_documents({})

    today_str = date.today().isoformat()
    trips_today = db.trips.count_documents({"trip_date": {"$regex": f"^{today_str}"}})

    pending_coaching = db.coaching_actions.count_documents({"status": {"$in": ["pending", "in_progress"]}})

    drivers = list(db.drivers.find({}, {"driver_id": 1}))
    high_risk = moderate = low_risk = 0
    total_score_sum = 0.0
    drivers_with_scores = 0

    for d in drivers:
        scores = list(db.scores.find({"driver_id": d["driver_id"]}))
        if not scores:
            continue
        drivers_with_scores += 1
        summary = calculate_driver_overall_score(scores)
        total_score_sum += summary["overall_score"]
        cat = summary["risk_category"]
        if cat == "High":
            high_risk += 1
        elif cat == "Moderate":
            moderate += 1
        else:
            low_risk += 1

    avg_fleet = round(total_score_sum / drivers_with_scores, 2) if drivers_with_scores else 0.0

    return {
        "total_drivers": total_drivers,
        "total_trips": total_trips,
        "avg_fleet_score": avg_fleet,
        "high_risk_drivers": high_risk,
        "moderate_risk_drivers": moderate,
        "low_risk_drivers": low_risk,
        "trips_today": trips_today,
        "pending_coaching_actions": pending_coaching,
    }


def mongo_fleet_analytics() -> dict:
    db = get_mongo_db()
    scores = list(db.scores.find({}))
    if not scores:
        return {
            "avg_score": 0.0, "score_distribution": {},
            "avg_speed_score": 0.0, "avg_braking_score": 0.0, "avg_acceleration_score": 0.0,
            "total_harsh_events": 0, "high_risk_count": 0, "drivers_with_trips": 0,
        }

    n = len(scores)
    avg = round(sum(s.get("trip_safety_score", 0.0) for s in scores) / n, 2)
    avs = round(sum(s.get("speed_score", 0.0) for s in scores) / n, 2)
    avb = round(sum(s.get("braking_score", 0.0) for s in scores) / n, 2)
    ava = round(sum(s.get("acceleration_score", 0.0) for s in scores) / n, 2)
    thr = sum(s.get("total_harsh_events", 0) for s in scores)
    hrc = sum(1 for s in scores if s.get("is_high_risk"))

    dist = {"Low Risk": 0, "Moderate Risk": 0, "High Risk": 0}
    for s in scores:
        lbl = s.get("risk_label", "Moderate Risk")
        if lbl in dist:
            dist[lbl] += 1

    dwt = len(db.scores.distinct("driver_id"))

    # Score buckets
    buckets = {f"{i*10}-{(i+1)*10}": 0 for i in range(10)}
    for s in scores:
        b = min(int(s.get("trip_safety_score", 0.0) // 10), 9)
        buckets[f"{b*10}-{(b+1)*10}"] += 1

    # Top harsh event drivers (aggregation)
    pipeline = [
        {"$group": {"_id": "$driver_id", "total": {"$sum": "$total_harsh_events"}}},
        {"$sort": {"total": -1}},
        {"$limit": 10},
    ]
    harsh_agg = list(db.scores.aggregate(pipeline))
    top_harsh = []
    for h in harsh_agg:
        did = h["_id"]
        drv = db.drivers.find_one({"driver_id": did})
        top_harsh.append({
            "driver_id": did,
            "name": drv.get("name", did) if drv else did,
            "total_harsh_events": int(h["total"]),
        })

    # Daily trips last 30 days
    today = date.today()
    daily = []
    for i in range(29, -1, -1):
        d_str = (today - timedelta(days=i)).isoformat()
        cnt = db.trips.count_documents({"trip_date": {"$regex": f"^{d_str}"}})
        daily.append({"date": d_str, "count": cnt})

    return {
        "avg_score": avg,
        "score_distribution": dist,
        "avg_speed_score": avs,
        "avg_braking_score": avb,
        "avg_acceleration_score": ava,
        "total_harsh_events": thr,
        "high_risk_count": hrc,
        "drivers_with_trips": dwt,
        "score_buckets": buckets,
        "top_harsh_drivers": top_harsh,
        "daily_trips": daily,
    }


def mongo_high_risk_drivers(limit: int = 50) -> List[dict]:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score

    drivers = list(db.drivers.find({}))
    results = []

    for drv in drivers:
        did = drv["driver_id"]
        scores = list(db.scores.find({"driver_id": did}))
        if not scores:
            continue
        summary = calculate_driver_overall_score(scores)
        if summary["risk_category"] != "High":
            continue

        latest_coaching = db.coaching_actions.find_one({"driver_id": did}, sort=[("created_at", -1)])
        coaching_status = latest_coaching.get("status") if latest_coaching else None

        n = len(scores)
        high_spd = sum(1 for s in scores if s.get("speed_risk"))
        high_brk = sum(1 for s in scores if s.get("braking_risk"))
        high_acc = sum(1 for s in scores if s.get("acceleration_risk"))
        factors = []
        if high_spd / n > 0.2: factors.append(f"Excessive speed ({high_spd}/{n} trips)")
        if high_brk / n > 0.2: factors.append(f"Harsh braking ({high_brk}/{n} trips)")
        if high_acc / n > 0.2: factors.append(f"Harsh acceleration ({high_acc}/{n} trips)")
        if not factors: factors.append("Combined risk factors")

        results.append({
            "driver_id": did,
            "driver_name": drv.get("name", did),
            "overall_score": summary["overall_score"],
            "risk_category": summary["risk_category"],
            "total_trips": summary["trip_count"],
            "latest_score": summary["latest_score"],
            "trend": summary["trend"],
            "coaching_status": coaching_status,
            "risk_factors": factors,
        })

    results.sort(key=lambda x: x["overall_score"])
    return results[:limit]


def mongo_driver_trend(driver_id: str) -> Optional[dict]:
    db = get_mongo_db()
    from app.utils.driver_analytics import calculate_driver_overall_score
    drv = db.drivers.find_one({"driver_id": driver_id})
    if not drv:
        return None

    scores = list(db.scores.find({"driver_id": driver_id}).sort("created_at", 1))
    summary = calculate_driver_overall_score(scores)

    trend_data = []
    for s in scores:
        trip = db.trips.find_one({"trip_id": s.get("trip_id")})
        tdate = trip.get("trip_date") if trip else s.get("created_at", "")[:10]
        trend_data.append({
            "trip_id": s.get("trip_id"),
            "trip_date": str(tdate),
            "trip_safety_score": float(s.get("trip_safety_score", 0.0)),
            "risk_category": s.get("risk_category", "Moderate"),
        })

    return {
        "driver_id": driver_id,
        "driver_name": drv.get("name", driver_id),
        "overall_score": summary["overall_score"],
        "risk_category": summary["risk_category"],
        "trend": summary["trend"],
        "trip_count": summary["trip_count"],
        "trend_data": trend_data,
    }


# Coaching
def mongo_get_coaching() -> List[dict]:
    db = get_mongo_db()
    return _clean_docs(db.coaching_actions.find().sort("created_at", -1))


def mongo_create_coaching(data: dict, current_user: dict) -> dict:
    db = get_mongo_db()
    drv = db.drivers.find_one({"driver_id": data["driver_id"]})
    if not drv:
        raise ValueError(f"Driver '{data['driver_id']}' not found.")

    user = db.users.find_one({"username": current_user.get("sub")})
    user_id = user.get("id", 1) if user else 1

    count = db.coaching_actions.count_documents({})
    now = datetime.utcnow().isoformat()

    rf = data.get("risk_factors")
    if isinstance(rf, list):
        rf = json.dumps(rf)

    fup = data.get("follow_up_date")
    if isinstance(fup, (date, datetime)):
        fup = fup.isoformat()

    doc = {
        "id": count + 1,
        "driver_id": data["driver_id"],
        "created_by": user_id,
        "reason": data["reason"],
        "risk_factors": rf,
        "coaching_notes": data.get("coaching_notes"),
        "action_taken": data.get("action_taken"),
        "status": data.get("status", "pending"),
        "follow_up_date": fup,
        "created_at": now,
        "updated_at": now,
    }
    db.coaching_actions.insert_one(dict(doc))
    return _clean_doc(doc)


def mongo_update_coaching(action_id: int, data: dict) -> Optional[dict]:
    db = get_mongo_db()
    ca = db.coaching_actions.find_one({"id": action_id})
    if not ca:
        return None

    updates = {}
    for k, v in data.items():
        if v is not None:
            if k == "risk_factors" and isinstance(v, list):
                v = json.dumps(v)
            if k == "follow_up_date" and isinstance(v, (date, datetime)):
                v = v.isoformat()
            updates[k] = v

    updates["updated_at"] = datetime.utcnow().isoformat()
    db.coaching_actions.update_one({"id": action_id}, {"$set": updates})
    return _clean_doc(db.coaching_actions.find_one({"id": action_id}))


def mongo_get_driver_coaching(driver_id: str) -> List[dict]:
    db = get_mongo_db()
    return _clean_docs(db.coaching_actions.find({"driver_id": driver_id}).sort("created_at", -1))
