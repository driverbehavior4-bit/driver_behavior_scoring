"""ORM Models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, nullable=False, index=True)
    email           = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), nullable=False, default="fleet_manager")
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    coaching_actions = relationship("CoachingAction", back_populates="creator")


class Driver(Base):
    __tablename__ = "drivers"
    id             = Column(Integer, primary_key=True, index=True)
    driver_id      = Column(String(20), unique=True, nullable=False, index=True)
    name           = Column(String(100), nullable=False)
    email          = Column(String(100))
    phone          = Column(String(20))
    license_number = Column(String(50))
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    trips           = relationship("Trip", back_populates="driver")
    scores          = relationship("Score", back_populates="driver")
    coaching_actions= relationship("CoachingAction", back_populates="driver")


class Trip(Base):
    __tablename__ = "trips"
    id                 = Column(Integer, primary_key=True, index=True)
    trip_id            = Column(String(50), unique=True, nullable=False, index=True)
    driver_id          = Column(String(20), ForeignKey("drivers.driver_id"), nullable=False, index=True)
    trip_date          = Column(Date)
    average_speed      = Column(Float, default=0.0)
    max_speed          = Column(Float, default=0.0)
    harsh_braking      = Column(Integer, default=0)
    harsh_acceleration = Column(Integer, default=0)
    trip_duration      = Column(Float, default=1.0)
    distance           = Column(Float)
    idle_time          = Column(Float)
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    driver = relationship("Driver", back_populates="trips")
    score  = relationship("Score", back_populates="trip", uselist=False)


class Score(Base):
    __tablename__ = "scores"
    id                      = Column(Integer, primary_key=True, index=True)
    trip_id                 = Column(String(50), ForeignKey("trips.trip_id"), unique=True, nullable=False, index=True)
    driver_id               = Column(String(20), ForeignKey("drivers.driver_id"), nullable=False, index=True)
    trip_safety_score       = Column(Float, nullable=False)
    risk_label              = Column(String(20), nullable=False)
    risk_category           = Column(String(20), nullable=False)
    speed_score             = Column(Float)
    braking_score           = Column(Float)
    acceleration_score      = Column(Float)
    speed_risk              = Column(Boolean, default=False)
    braking_risk            = Column(Boolean, default=False)
    acceleration_risk       = Column(Boolean, default=False)
    total_harsh_events      = Column(Integer, default=0)
    harsh_events_per_minute = Column(Float, default=0.0)
    is_high_risk            = Column(Boolean, default=False)
    created_at              = Column(DateTime, default=datetime.utcnow, nullable=False)
    trip   = relationship("Trip",   back_populates="score")
    driver = relationship("Driver", back_populates="scores")


class CoachingAction(Base):
    __tablename__ = "coaching_actions"
    id             = Column(Integer, primary_key=True, index=True)
    driver_id      = Column(String(20), ForeignKey("drivers.driver_id"), nullable=False, index=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason         = Column(Text, nullable=False)
    risk_factors   = Column(Text)
    coaching_notes = Column(Text)
    action_taken   = Column(Text)
    status         = Column(String(20), nullable=False, default="pending")
    follow_up_date = Column(Date)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    driver  = relationship("Driver", back_populates="coaching_actions")
    creator = relationship("User",   back_populates="coaching_actions")
