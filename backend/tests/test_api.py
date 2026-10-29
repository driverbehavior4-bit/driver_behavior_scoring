"""
backend/tests/test_api.py
Comprehensive API test suite.
"""
import urllib.request, json, urllib.error, sys

BASE = "http://localhost:8000"
passed = failed = 0

def req(endpoint, method=None, body=None, token=None):
    url = BASE + endpoint
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body else None
    if method is None: method = "POST" if data else "GET"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        return None, (e.code, e.read().decode())

def ok(label, result, err, key=None):
    global passed, failed
    if err:
        print(f"  [FAIL] {label}: HTTP {err[0]}")
        failed += 1; return None
    if key and (not isinstance(result, dict) or key not in result):
        if isinstance(result, list):
            print(f"  [OK]  {label} ({len(result)} items)"); passed += 1; return result
        print(f"  [FAIL] {label}: missing '{key}'"); failed += 1; return None
    print(f"  [OK]  {label}")
    passed += 1; return result

print("=" * 55)
print("  Driver Behavior Scoring — API Test Suite")
print("=" * 55)

# Health
r, e = req("/health"); ok("GET /health", r, e, "status")

# Login admin
r, e = req("/auth/login", body={"username":"admin","password":"admin123"})
tok  = ok("POST /auth/login (admin)", r, e, "access_token")
admin_token = tok.get("access_token","") if tok else ""

# Login fleet_manager
r, e = req("/auth/login", body={"username":"fleet_manager","password":"fleet123"})
ok("POST /auth/login (fleet_manager)", r, e, "access_token")

# Wrong password -> 401
r, e = req("/auth/login", body={"username":"admin","password":"wrong"})
if e and e[0] == 401: print("  [OK]  Wrong password -> 401"); passed += 1
else: print(f"  [FAIL] Wrong password not 401: {r}"); failed += 1

# Unauthorized access
r, e = req("/analytics/dashboard")
if e and e[0] in (401,403): print("  [OK]  No-token -> 401/403"); passed += 1
else: print(f"  [FAIL] No-token not blocked: {r}"); failed += 1

if not admin_token:
    print("[FATAL] Login failed, cannot continue"); sys.exit(1)

# Drivers
r, e = req("/drivers", token=admin_token)
ok("GET /drivers", r, e)
driver_id = "D001"
if isinstance(r, list) and r:
    driver_id = r[0]["driver_id"]
    print(f"         First driver: {driver_id} - {r[0].get('name')} (score={r[0].get('overall_score')})")

# Trips
r, e = req("/trips?limit=5", token=admin_token)
ok("GET /trips?limit=5", r, e, "trips")
if r: print(f"         {r.get('total',0)} total trips")

# Driver trips
r, e = req(f"/drivers/{driver_id}/trips", token=admin_token)
ok(f"GET /drivers/{driver_id}/trips", r, e, "trips")

# Driver score summary
r, e = req(f"/scores/driver/{driver_id}", token=admin_token)
ok(f"GET /scores/driver/{driver_id}", r, e, "overall_score")
if r: print(f"         score={r['overall_score']}, risk={r.get('risk_category')}, trips={r.get('trip_count')}")

# Fleet analytics
r, e = req("/analytics/fleet", token=admin_token)
ok("GET /analytics/fleet", r, e, "avg_score")
if r: print(f"         avg_score={r.get('avg_score')}, harsh_events={r.get('total_harsh_events')}")

# Dashboard
r, e = req("/analytics/dashboard", token=admin_token)
ok("GET /analytics/dashboard", r, e, "total_drivers")
if r: print(f"         drivers={r['total_drivers']}, trips={r['total_trips']}, fleet_score={r['avg_fleet_score']}")

# High-risk drivers
r, e = req("/analytics/high-risk-drivers", token=admin_token)
ok("GET /analytics/high-risk-drivers", r, e)
if isinstance(r, list): print(f"         {len(r)} high-risk drivers")

# Driver trend
r, e = req(f"/analytics/driver/{driver_id}/trend", token=admin_token)
ok(f"GET /analytics/driver/{driver_id}/trend", r, e, "trend_data")
if r: print(f"         {len(r.get('trend_data',[]))} trend points")

# Create new trip
r, e = req("/trips", body={"driver_id":driver_id,"trip_date":"2026-10-02","average_speed":95.0,
           "max_speed":130.0,"harsh_braking":6,"harsh_acceleration":5,
           "trip_duration":45.0,"distance":71.0}, token=admin_token)
ok("POST /trips (auto-generate trip_id)", r, e, "trip_safety_score")
if r: print(f"         score={r.get('trip_safety_score')}, risk={r.get('risk_category')}")

# Create trip with explicit trip_id
r, e = req("/trips", body={"driver_id":driver_id,"trip_id":"TEST-EXPLICIT-001","trip_date":"2026-10-02",
           "average_speed":60.0,"max_speed":80.0,"harsh_braking":1,"harsh_acceleration":1,
           "trip_duration":30.0}, token=admin_token)
ok("POST /trips (explicit trip_id)", r, e, "trip_safety_score")
if r: print(f"         score={r.get('trip_safety_score')}, risk={r.get('risk_category')}")

# Duplicate trip_id -> 409
r, e = req("/trips", body={"driver_id":driver_id,"trip_id":"TEST-EXPLICIT-001","trip_date":"2026-10-02",
           "average_speed":60.0,"max_speed":80.0,"harsh_braking":1,"harsh_acceleration":1,
           "trip_duration":30.0}, token=admin_token)
if e and e[0] == 409: print("  [OK]  Duplicate trip_id -> 409"); passed += 1
else: print(f"  [FAIL] Duplicate trip_id not 409"); failed += 1

# Invalid speed
r, e = req("/trips", body={"driver_id":driver_id,"trip_date":"2026-10-02",
           "average_speed":100.0,"max_speed":50.0,"harsh_braking":0,"harsh_acceleration":0,
           "trip_duration":30.0}, token=admin_token)
if e and e[0] in (422, 400): print("  [OK]  Invalid speed (avg>max) -> 422"); passed += 1
else: print(f"  [FAIL] Invalid speed not caught: {r}"); failed += 1

# Coaching create
r, e = req("/coaching", body={"driver_id":driver_id,"reason":"Repeated speeding",
           "risk_factors":["Speed","Braking"],"coaching_notes":"Warning issued",
           "action_taken":"Verbal warning","status":"pending"}, token=admin_token)
ok("POST /coaching", r, e, "id")
coaching_id = r.get("id") if r else None
if r: print(f"         coaching id={coaching_id}, status={r.get('status')}")

# Update coaching
if coaching_id:
    r, e = req(f"/coaching/{coaching_id}", method="PUT",
               body={"status":"in_progress","coaching_notes":"Follow-up scheduled"},
               token=admin_token)
    ok(f"PUT /coaching/{coaching_id}", r, e, "status")
    if r: print(f"         status -> {r.get('status')}")

# List coaching
r, e = req("/coaching", token=admin_token)
ok("GET /coaching", r, e)
if isinstance(r, list): print(f"         {len(r)} coaching actions total")

# Driver coaching
r, e = req(f"/coaching/driver/{driver_id}", token=admin_token)
ok(f"GET /coaching/driver/{driver_id}", r, e)

# Create driver
r, e = req("/drivers", body={"driver_id":"D999","name":"Test Driver",
           "email":"test@fleet.com","phone":"555-0000","license_number":"TEST999"},
           token=admin_token)
ok("POST /drivers", r, e, "driver_id")

# Update driver
r, e = req("/drivers/D999", method="PUT", body={"name":"Updated Test Driver"}, token=admin_token)
ok("PUT /drivers/D999", r, e, "name")

print()
print("=" * 55)
print(f"  Results: {passed} passed, {failed} failed out of {passed+failed}")
print("=" * 55)
sys.exit(0 if failed == 0 else 1)
