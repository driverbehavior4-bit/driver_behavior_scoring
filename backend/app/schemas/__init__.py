"""All Pydantic v2 schemas"""
from typing import Optional, List, Any
from datetime import datetime, date
from pydantic import BaseModel, field_validator


# ── Auth ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ── Driver ───────────────────────────────────────────────────────────────────
class DriverBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None

class DriverCreate(DriverBase):
    driver_id: str

class DriverUpdate(DriverBase):
    name: Optional[str] = None

class DriverResponse(BaseModel):
    id: int
    driver_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    created_at: datetime
    overall_score: Optional[float] = None
    risk_category: Optional[str] = None
    is_high_risk: Optional[bool] = None
    trip_count: Optional[int] = None
    class Config: from_attributes = True

class DriverList(BaseModel):
    total: int
    drivers: List[DriverResponse]


# ── Trip ─────────────────────────────────────────────────────────────────────
class TripCreate(BaseModel):
    trip_id: Optional[str] = None
    driver_id: str
    trip_date: Optional[date] = None
    average_speed: float = 0.0
    max_speed: float = 0.0
    harsh_braking: int = 0
    harsh_acceleration: int = 0
    trip_duration: float = 1.0
    distance: Optional[float] = None
    idle_time: Optional[float] = None

    @field_validator("average_speed", "max_speed", "trip_duration")
    @classmethod
    def non_negative(cls, v):
        if v < 0: raise ValueError("Must be >= 0")
        return v

    @field_validator("harsh_braking", "harsh_acceleration")
    @classmethod
    def non_negative_int(cls, v):
        if v < 0: raise ValueError("Must be >= 0")
        return v

class TripResponse(BaseModel):
    id: int
    trip_id: str
    driver_id: str
    trip_date: Optional[date] = None
    average_speed: float
    max_speed: float
    harsh_braking: int
    harsh_acceleration: int
    trip_duration: float
    distance: Optional[float] = None
    idle_time: Optional[float] = None
    created_at: datetime
    class Config: from_attributes = True

class TripList(BaseModel):
    total: int
    trips: List[TripResponse]


# ── Score ─────────────────────────────────────────────────────────────────────
class ScoreResponse(BaseModel):
    id: int
    trip_id: str
    driver_id: str
    trip_safety_score: float
    risk_label: str
    risk_category: str
    speed_score: Optional[float] = None
    braking_score: Optional[float] = None
    acceleration_score: Optional[float] = None
    speed_risk: Optional[bool] = None
    braking_risk: Optional[bool] = None
    acceleration_risk: Optional[bool] = None
    total_harsh_events: Optional[int] = None
    harsh_events_per_minute: Optional[float] = None
    is_high_risk: bool
    created_at: datetime
    class Config: from_attributes = True

class DriverScoreSummary(BaseModel):
    driver_id: str
    driver_name: str
    overall_score: float
    risk_category: str
    is_high_risk: bool
    trip_count: int
    trend: str
    avg_score: float
    latest_score: float


# ── Coaching ──────────────────────────────────────────────────────────────────
class CoachingCreate(BaseModel):
    driver_id: str
    reason: str
    risk_factors: Optional[Any] = None
    coaching_notes: Optional[str] = None
    action_taken: Optional[str] = None
    status: str = "pending"
    follow_up_date: Optional[date] = None

class CoachingUpdate(BaseModel):
    reason: Optional[str] = None
    risk_factors: Optional[Any] = None
    coaching_notes: Optional[str] = None
    action_taken: Optional[str] = None
    status: Optional[str] = None
    follow_up_date: Optional[date] = None

class CoachingResponse(BaseModel):
    id: int
    driver_id: str
    created_by: int
    reason: str
    risk_factors: Optional[str] = None
    coaching_notes: Optional[str] = None
    action_taken: Optional[str] = None
    status: str
    follow_up_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


# ── Analytics ─────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_drivers: int
    total_trips: int
    avg_fleet_score: float
    high_risk_drivers: int
    moderate_risk_drivers: int
    low_risk_drivers: int
    trips_today: int
    pending_coaching_actions: int

class FleetAnalytics(BaseModel):
    avg_score: float
    score_distribution: dict
    avg_speed_score: float
    avg_braking_score: float
    avg_acceleration_score: float
    total_harsh_events: int
    high_risk_count: int
    drivers_with_trips: int
    score_buckets: Optional[dict] = None
    top_harsh_drivers: Optional[list] = None
    daily_trips: Optional[list] = None

class HighRiskDriver(BaseModel):
    driver_id: str
    driver_name: str
    overall_score: float
    risk_category: str
    total_trips: int
    latest_score: float
    trend: str
    coaching_status: Optional[str] = None
    risk_factors: Optional[list] = None

class DriverTrendPoint(BaseModel):
    trip_id: str
    trip_date: Optional[str] = None
    trip_safety_score: float
    risk_category: str

class DriverTrend(BaseModel):
    driver_id: str
    driver_name: str
    overall_score: float
    risk_category: str
    trend: str
    trip_count: int
    trend_data: List[DriverTrendPoint]
