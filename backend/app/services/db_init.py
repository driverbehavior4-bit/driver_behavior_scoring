"""backend/app/services/db_init.py — DB initialization, seeding from CSV."""
import os, csv, json
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.database.connection import Base, engine, SessionLocal
from app.models import User, Driver, Trip, Score, CoachingAction  # noqa
from app.utils.security import hash_password
from app.utils.scoring import calculate_trip_score


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created / verified.")


def seed_users(db: Session):
    for udata in [
        {"username":"admin",        "email":"admin@fleet.com",   "password":"admin123",  "role":"admin"},
        {"username":"fleet_manager","email":"manager@fleet.com","password":"fleet123","role":"fleet_manager"},
    ]:
        if not db.query(User).filter(User.username == udata["username"]).first():
            db.add(User(username=udata["username"], email=udata["email"],
                        hashed_password=hash_password(udata["password"]),
                        role=udata["role"], is_active=True))
            print(f"[DB] Created user: {udata['username']}")
    db.commit()


def seed_demo_drivers(db: Session, count: int = 50):
    existing = db.query(Driver).count()
    if existing >= count:
        print(f"[DB] {existing} drivers already in DB, skipping seed.")
        return
    first = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
             "William","Barbara","David","Susan","Richard","Jessica","Joseph","Sarah",
             "Thomas","Karen","Charles","Lisa","Christopher","Nancy","Daniel","Betty",
             "Matthew","Margaret","Anthony","Sandra","Donald","Ashley","Mark","Dorothy",
             "Paul","Kimberly","Steven","Emily","George","Donna","Kenneth","Michelle",
             "Andrew","Carol","Joshua","Amanda","Kevin","Melissa","Brian","Deborah","Edward","Stephanie"]
    last  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
             "Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor",
             "Moore","Jackson","Martin","Lee","Perez","Thompson","White","Harris",
             "Sanchez","Clark","Ramirez","Lewis","Robinson","Walker"]
    import random; random.seed(42)
    created = 0
    for i in range(1, count+1):
        did = f"D{i:03d}"
        if db.query(Driver).filter(Driver.driver_id == did).first():
            continue
        fn = random.choice(first); ln = random.choice(last)
        db.add(Driver(driver_id=did, name=f"{fn} {ln}",
                      email=f"{fn.lower()}.{ln.lower()}{i}@fleet.com",
                      phone=f"+1-555-{random.randint(1000,9999)}",
                      license_number=f"LIC{i:05d}"))
        created += 1
    db.commit()
    print(f"[DB] Created {created} demo drivers.")


def load_csv_data(db: Session, csv_path: str):
    if not os.path.exists(csv_path):
        print(f"[DB] CSV not found: {csv_path}")
        return

    existing_trips = db.query(Trip).count()
    if existing_trips > 0:
        print(f"[DB] {existing_trips} trips already in DB, skipping CSV import.")
        return

    print(f"[DB] Loading from {csv_path} ...")
    drivers_added = trips_added = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def _f(k, d=0.0):
                try: return float(row.get(k, d) or d)
                except: return d
            def _i(k, d=0):
                try: return int(float(row.get(k, d) or d))
                except: return d

            did   = row.get("driver_id","").strip()
            tid   = row.get("trip_id","").strip()
            dname = row.get("driver_name", f"Driver {did}").strip()
            if not did or not tid:
                continue

            # Ensure driver
            if not db.query(Driver).filter(Driver.driver_id == did).first():
                db.add(Driver(driver_id=did, name=dname,
                              email=f"{did.lower()}@fleet.com",
                              phone="", license_number=f"LIC-{did}"))
                db.flush()
                drivers_added += 1

            if db.query(Trip).filter(Trip.trip_id == tid).first():
                continue

            trip_date = None
            ds = row.get("trip_date","")
            if ds:
                for fmt in ("%Y-%m-%d","%d/%m/%Y","%m/%d/%Y"):
                    try: trip_date = datetime.strptime(ds, fmt).date(); break
                    except: pass

            trip = Trip(trip_id=tid, driver_id=did, trip_date=trip_date,
                        average_speed=_f("average_speed"), max_speed=_f("max_speed"),
                        harsh_braking=_i("harsh_braking"), harsh_acceleration=_i("harsh_acceleration"),
                        trip_duration=max(_f("trip_duration",1.0), 0.1),
                        distance=_f("distance") or None, idle_time=_f("idle_time") or None)
            db.add(trip)

            sd = calculate_trip_score(trip.max_speed, trip.harsh_braking,
                                      trip.harsh_acceleration, trip.trip_duration, trip.average_speed)
            db.add(Score(trip_id=tid, driver_id=did,
                         trip_safety_score=sd["trip_safety_score"],
                         risk_label=sd["risk_label"], risk_category=sd["risk_category"],
                         speed_score=sd["speed_score"], braking_score=sd["braking_score"],
                         acceleration_score=sd["acceleration_score"],
                         speed_risk=sd["speed_risk"], braking_risk=sd["braking_risk"],
                         acceleration_risk=sd["acceleration_risk"],
                         total_harsh_events=sd["total_harsh_events"],
                         harsh_events_per_minute=sd["harsh_events_per_minute"],
                         is_high_risk=sd["is_high_risk"]))
            trips_added += 1
            if trips_added % 200 == 0:
                db.commit()
                print(f"[DB]   ... {trips_added} trips loaded ...")

    db.commit()
    print(f"[DB] CSV import done: {drivers_added} drivers, {trips_added} trips.")


def initialize_database():
    create_tables()
    db = SessionLocal()
    try:
        seed_users(db)
        # Find CSV relative to backend dir
        here     = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.normpath(os.path.join(here, "..", "..", "..", "data", "raw", "driving_data.csv"))
        if os.path.exists(csv_path):
            load_csv_data(db, csv_path)
        else:
            seed_demo_drivers(db)
    finally:
        db.close()
    print("[DB] Initialization complete.")
