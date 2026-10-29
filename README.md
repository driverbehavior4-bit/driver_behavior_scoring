# 🛡️ Driver Behavior Scoring System for Fleet Safety

A complete, end-to-end fleet safety web application that analyzes trip-level driving behavior, generates safety risk scores, identifies high-risk drivers, and provides a coaching workflow — all backed by a machine-learning model and a professional dashboard.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Technologies](#technologies)
5. [Project Structure](#project-structure)
6. [Dataset Description](#dataset-description)
7. [Feature Engineering](#feature-engineering)
8. [ML Methodology](#ml-methodology)
9. [Model Evaluation](#model-evaluation)
10. [Scoring Formula](#scoring-formula)
11. [Database Setup](#database-setup)
12. [Backend Setup](#backend-setup)
13. [Frontend Setup](#frontend-setup)
14. [Environment Variables](#environment-variables)
15. [How to Run](#how-to-run)
16. [API Documentation](#api-documentation)
17. [Testing](#testing)
18. [Demo Credentials](#demo-credentials)
19. [URLs & Ports](#urls--ports)
20. [Known Limitations & Future Work](#known-limitations--future-work)

---

## Project Overview

**Problem Statement:**  
Fleet operators lack real-time visibility into driver safety behavior. Manual audits are slow, inconsistent, and miss critical patterns. High-risk drivers cause accidents, insurance claims, and liability.

**Objective:**  
Build an automated system that:
- Ingests trip telematics data (speed, braking, acceleration)
- Scores every trip using a documented formula + ML model
- Identifies high-risk drivers from their trip history
- Provides fleet managers with a dashboard, analytics, and a coaching workflow

---

## Features

| Feature | Description |
|---|---|
| 🔐 Authentication | JWT-based login, role-based access (Admin / Fleet Manager) |
| 📊 Dashboard | Fleet KPIs, risk distribution charts, top-risk driver bar chart |
| 👥 Drivers | List, search, filter, view detailed driver profile |
| 🚗 Trip Logging | Add trips via form, auto-calculate safety score |
| 🤖 ML Scoring | Pure-NumPy Decision Tree (94% F1) + formula-based score |
| 🚨 High-Risk | Auto-identified from scoring engine, with risk factors |
| 📋 Coaching | Create/update coaching actions with status tracking |
| 📈 Analytics | Score distribution, harsh events chart, daily trips trend |

---

## Architecture

```
Frontend (HTML/CSS/JS)
        │  HTTP + JWT
        ▼
FastAPI Backend (port 8000)
        │
        ├── Auth (JWT via python-jose + bcrypt)
        ├── Scoring Engine (pure Python formula)
        ├── Analytics Engine (MongoDB Aggregations / Queries)
        │
        ▼
MongoDB Database (Local / Atlas Cloud)
        │
ML Models (joblib)
        └── DecisionTreeNP (pure NumPy, no sklearn)
```

---

## Technologies

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | **MongoDB** (Local / Atlas) via PyMongo (SQL fallback available) |
| Auth | JWT (python-jose), bcrypt (passlib) |
| ML | Pure Python/NumPy Decision Tree (sklearn DLLs blocked) |
| Data | Pandas, NumPy |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Charts | Chart.js 4.x |
| Persistence | joblib (model), dotenv (config) |

---

## Project Structure

```
driver-behavior-scoring/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── database/connection.py  # SQLAlchemy engine + session
│   │   ├── models/__init__.py      # ORM: User, Driver, Trip, Score, CoachingAction
│   │   ├── schemas/__init__.py     # Pydantic schemas (all)
│   │   ├── routes/__init__.py      # All API routes
│   │   ├── services/
│   │   │   ├── db_init.py          # DB initialization + CSV seeding
│   │   │   └── trip_service.py     # Trip processing + scoring
│   │   └── utils/
│   │       ├── security.py         # JWT + bcrypt
│   │       ├── scoring.py          # Trip scoring formula
│   │       └── driver_analytics.py # Driver-level aggregation
│   ├── tests/test_api.py           # 23-test API suite
│   ├── .env                        # Dev environment (not committed)
│   ├── .env.example                # Template
│   └── requirements.txt
├── frontend/
│   ├── index.html                  # Login page
│   ├── dashboard.html              # Main SPA dashboard
│   └── src/
│       ├── css/main.css            # Complete stylesheet
│       └── js/
│           ├── auth.js             # JWT session management
│           ├── api.js              # API service layer
│           └── charts.js           # Chart.js wrappers
├── data/
│   ├── generate_data.py            # Synthetic dataset generator
│   ├── raw/driving_data.csv        # 1000 trip records (generated)
│   └── processed/processed_data.csv # Feature-engineered data
├── ml/
│   ├── preprocessing/pipeline.py   # Preprocessing + feature engineering
│   ├── training/
│   │   ├── train_model.py          # Pure-NumPy Decision Tree training
│   │   └── score_driver.py         # Driver-level scoring
│   └── models/
│       ├── best_model.joblib        # Trained model artifact
│       └── model_metadata.json     # Model metrics + formula
├── database/schema.sql             # MySQL production schema
├── .gitignore
└── README.md
```

---

## Dataset Description

**Source:** Synthetic telematics data generated by `data/generate_data.py`  
**Records:** 1,000 trips across 50 drivers  
**Seed:** 42 (fully reproducible)

| Field | Type | Description |
|---|---|---|
| driver_id | string | D001–D050 |
| driver_name | string | Generated name |
| trip_id | string | T00001–T01000 |
| trip_date | date | Random within last 180 days |
| average_speed | float | km/h |
| max_speed | float | average + 5–50 km/h |
| harsh_braking | int | Count of harsh braking events |
| harsh_acceleration | int | Count of harsh accel. events |
| trip_duration | float | Minutes |
| distance | float | km (trip_duration × avg_speed / 60) |
| idle_time | float | Minutes |

**Driver profiles:**
- D001–D010: Aggressive (high speed, many harsh events) → High Risk
- D011–D025: Moderate behavior → Moderate Risk
- D026–D050: Safe behavior → Low Risk

---

## Feature Engineering

| Feature | Formula |
|---|---|
| speed_difference | max_speed − average_speed |
| total_harsh_events | harsh_braking + harsh_acceleration |
| harsh_events_per_minute | total_harsh_events / trip_duration |
| speed_risk | 1 if max_speed > 100, else 0 |
| braking_risk | 1 if harsh_braking ≥ 4, else 0 |
| acceleration_risk | 1 if harsh_acceleration ≥ 4, else 0 |
| risk_indicator | speed_risk + braking_risk + acceleration_risk |

---

## ML Methodology

**Algorithm:** Pure-Python/NumPy Decision Tree Classifier (`DecisionTreeNP`)

> **Why custom?** scikit-learn C-extension DLLs are blocked by Application Control Policy on this machine. A full Decision Tree was re-implemented using only NumPy: Gini impurity splits, recursive tree building, and custom evaluation metrics.

**Pipeline:**
1. Load processed CSV
2. Select 11 feature columns
3. Stratified 80/20 train/test split (seed=42)
4. Train 3 variants (max_depth 5, 8, 12)
5. Select best by weighted F1
6. Save with joblib

**Target classes:**
- 0 = Low Risk (trip_safety_score ≥ 70)
- 1 = Moderate Risk (40 ≤ score < 70)
- 2 = High Risk (score < 40)

---

## Model Evaluation

| Model | Accuracy | F1 |
|---|---|---|
| DecisionTreeNP(depth=5) | **94.06%** | **0.9409** ✅ Best |
| DecisionTreeNP(depth=8) | 93.56% | 0.9363 |
| DecisionTreeNP(depth=12) | 93.56% | 0.9363 |

Confusion Matrix (depth=5, test set of 202 trips):
```
              Predicted
              Low  Mod  High
Actual Low  [ 93,   8,    0]
       Mod  [  2,  54,    2]
       High [  0,   0,   43]
```

---

## Scoring Formula

The **same formula** is used in the ML pipeline, the backend API, and the frontend display:

```
speed_score        = clip(100 − (max_speed − 80) × 2, 0, 100)
braking_score      = clip(100 − harsh_braking × 10, 0, 100)
acceleration_score = clip(100 − harsh_acceleration × 10, 0, 100)
trip_safety_score  = speed_score × 0.4 + braking_score × 0.3 + acceleration_score × 0.3
```

**Risk categories:**
- ≥ 70 → Low Risk
- 40–69 → Moderate Risk
- < 40 → High Risk

**Driver overall score:**  
Recency-weighted average of trip scores. Recent trips carry proportionally higher weight.

**High-risk flag:**  
`overall_score < 40` OR `(overall_score < 55 AND last_5_avg < 45)`

---

## Database Setup

### 🍃 MongoDB (Default Database)
The application natively connects to **MongoDB** (both Local and MongoDB Atlas Cloud).
- **Default Database:** `driver_safety`
- **Default URI:** `mongodb://localhost:27017`
- **Collections:** `users`, `drivers`, `trips`, `scores`, `coaching_actions`
- **Atlas URI Example:** `mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority`

#### Automatic Initialization & Seeding:
When the backend starts, it automatically connects to MongoDB, creates collections with unique indexes, and seeds:
- 2 default users (`admin`, `fleet_manager`)
- 50 drivers
- 1,000 trips with precalculated risk scores from `data/raw/driving_data.csv`

#### Standalone Seeding:
```bash
python database/mongo_seed.py
```

#### MongoDB Shell (`mongosh`) Script:
```bash
mongosh "mongodb://localhost:27017/driver_safety" database/mongo_init.js
```

### 🗄️ SQL Fallback (SQLite / MySQL)
If you wish to switch back to SQLite or MySQL:
Set `DATABASE_TYPE=sqlite` in `backend/.env`.
For MySQL:
```bash
mysql -u root -p < database/schema.sql
```
Set `DATABASE_URL=mysql+pymysql://fleet_user:password@localhost:3306/driver_safety` in `backend/.env`.

---

## Backend Setup

```bash
pip install -r backend/requirements.txt
```

---

## Frontend Setup

No build step needed. Open `frontend/index.html` directly in a browser.  
Requires the backend to be running on `http://localhost:8000`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_TYPE` | `mongodb` | Database engine (`mongodb` or `sqlite`) |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection URI (local or Atlas) |
| `MONGODB_DB_NAME` | `driver_safety` | MongoDB database name |
| `DATABASE_URL` | `sqlite:///./driver_safety.db` | SQL connection string (if using SQLite) |
| `SECRET_KEY` | (dev key) | JWT signing key — **change in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |

Copy `backend/.env.example` to `backend/.env` and update values.

---

## How to Run

### Step 1 — Generate Data & Train Model (one-time)
```bash
cd driver-behavior-scoring

# Generate 1000 synthetic trips
python data/generate_data.py

# Preprocess + engineer features
python -c "
import sys; sys.path.insert(0,'.')
from ml.preprocessing.pipeline import *
df = load_raw_data('data/raw/driving_data.csv')
df = preprocess(df); df = engineer_features(df)
save_processed(df, 'data/processed/processed_data.csv')
"

# Train ML model
python ml/training/train_model.py
```

### Step 2 — Start Backend
```bash
cd driver-behavior-scoring/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
The backend will:
- Create database tables
- Seed admin & fleet_manager users
- Import all 1000 trips from CSV with calculated scores

### Step 3 — Open Frontend
Open in browser:
```
frontend/index.html
```
Or serve with Python:
```bash
cd driver-behavior-scoring/frontend
python -m http.server 3000
```
Then open: `http://localhost:3000`

---

## API Documentation

Interactive Swagger UI: **http://localhost:8000/docs**  
ReDoc: **http://localhost:8000/redoc**

### Key Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | No | Login → JWT token |
| GET | `/drivers` | Yes | List all drivers with scores |
| POST | `/drivers` | Yes | Create driver |
| GET | `/drivers/{id}/trips` | Yes | Driver trip history |
| GET | `/trips` | Yes | All trips (paginated) |
| POST | `/trips` | Yes | Add trip → auto-scored |
| GET | `/scores/driver/{id}` | Yes | Driver overall score |
| GET | `/analytics/dashboard` | Yes | KPI stats |
| GET | `/analytics/fleet` | Yes | Fleet-wide analytics |
| GET | `/analytics/high-risk-drivers` | Yes | High-risk list |
| GET | `/analytics/driver/{id}/trend` | Yes | Score trend |
| GET | `/coaching` | Yes | All coaching actions |
| POST | `/coaching` | Yes | Create coaching action |
| PUT | `/coaching/{id}` | Yes | Update coaching action |

---

## Testing

```bash
# Run API test suite (backend must be running)
cd driver-behavior-scoring/backend
python tests/test_api.py
```

**Test coverage (23 tests):**
- Health check
- Login (admin + fleet_manager)
- Wrong password → 401
- Unauthorized access → 401
- Driver CRUD
- Trip CRUD + auto-scoring
- Duplicate trip_id → 409
- Invalid speed (avg > max) → 422
- Score retrieval
- Fleet analytics
- Dashboard stats
- High-risk driver identification
- Driver trend
- Coaching CRUD

**Result:** ✅ 23/23 passed

---

## Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Fleet Manager | `fleet_manager` | `fleet123` |

> ⚠️ Change these in production using environment variables.

---

## URLs & Ports

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Frontend | Open `frontend/index.html` in browser |
| Frontend (served) | http://localhost:3000 |

---

## Known Limitations & Future Work

| Limitation | Status | Workaround / Plan |
|---|---|---|
| MySQL not installed | SQLite used for dev | Set `DATABASE_URL` for MySQL in production |
| sklearn DLLs blocked | Pure-NumPy Decision Tree | Same accuracy, fully functional |
| No frontend build pipeline | Vanilla JS | Works with direct file open or `python -m http.server` |
| Passwords hashed at startup | bcrypt via passlib | Secure; change SECRET_KEY in production |
| No email notifications | Not implemented | Planned: SMTP coaching reminders |
| No real-time data streaming | Batch CSV loading | Planned: WebSocket/MQTT integration |
| No pagination on driver modal | Returns up to 100 trips | Planned: lazy loading |

---

## Week Plan Summary

| Week | Deliverable | Status |
|---|---|---|
| 1 | Requirements analysis, documentation | ✅ |
| 2 | Synthetic dataset generation + exploration | ✅ |
| 3 | Preprocessing + feature engineering | ✅ |
| 4 | ML model training + evaluation + scoring API | ✅ |
| 5 | FastAPI backend + SQLite DB + auth + all APIs | ✅ |
| 6 | Frontend dashboard (SPA, Chart.js, coaching) | ✅ |
| 7 | Testing, integration, README, deployment docs | ✅ |
