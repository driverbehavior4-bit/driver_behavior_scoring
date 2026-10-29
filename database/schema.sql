-- database/schema.sql
-- MySQL-compatible production schema for Driver Behavior Scoring System
-- Usage: mysql -u root -p < database/schema.sql

CREATE DATABASE IF NOT EXISTS driver_safety CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE driver_safety;

-- Users table (authentication + RBAC)
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            ENUM('admin','fleet_manager') NOT NULL DEFAULT 'fleet_manager',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB;

-- Drivers table
CREATE TABLE IF NOT EXISTS drivers (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    driver_id      VARCHAR(20)  NOT NULL UNIQUE,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(100),
    phone          VARCHAR(20),
    license_number VARCHAR(50),
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_driver_id (driver_id)
) ENGINE=InnoDB;

-- Trips table
CREATE TABLE IF NOT EXISTS trips (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    trip_id            VARCHAR(50) NOT NULL UNIQUE,
    driver_id          VARCHAR(20) NOT NULL,
    trip_date          DATE,
    average_speed      FLOAT DEFAULT 0.0,
    max_speed          FLOAT DEFAULT 0.0,
    harsh_braking      INT   DEFAULT 0,
    harsh_acceleration INT   DEFAULT 0,
    trip_duration      FLOAT DEFAULT 1.0  COMMENT 'minutes',
    distance           FLOAT              COMMENT 'km, nullable',
    idle_time          FLOAT              COMMENT 'minutes, nullable',
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trip_id  (trip_id),
    INDEX idx_driver   (driver_id),
    INDEX idx_date     (trip_date),
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Scores table (one-to-one with trips)
CREATE TABLE IF NOT EXISTS scores (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    trip_id                 VARCHAR(50) NOT NULL UNIQUE,
    driver_id               VARCHAR(20) NOT NULL,
    trip_safety_score       FLOAT NOT NULL  COMMENT '0-100',
    risk_label              VARCHAR(20) NOT NULL  COMMENT 'Low Risk / Moderate Risk / High Risk',
    risk_category           VARCHAR(20) NOT NULL  COMMENT 'Low / Moderate / High',
    speed_score             FLOAT,
    braking_score           FLOAT,
    acceleration_score      FLOAT,
    speed_risk              BOOLEAN DEFAULT FALSE,
    braking_risk            BOOLEAN DEFAULT FALSE,
    acceleration_risk       BOOLEAN DEFAULT FALSE,
    total_harsh_events      INT DEFAULT 0,
    harsh_events_per_minute FLOAT DEFAULT 0.0,
    is_high_risk            BOOLEAN DEFAULT FALSE,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trip     (trip_id),
    INDEX idx_driver   (driver_id),
    FOREIGN KEY (trip_id)   REFERENCES trips(trip_id)   ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Coaching actions table
CREATE TABLE IF NOT EXISTS coaching_actions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    driver_id      VARCHAR(20) NOT NULL,
    created_by     INT NOT NULL,
    reason         TEXT NOT NULL,
    risk_factors   TEXT         COMMENT 'JSON array of risk factor strings',
    coaching_notes TEXT,
    action_taken   TEXT,
    status         ENUM('pending','in_progress','completed') NOT NULL DEFAULT 'pending',
    follow_up_date DATE,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_driver (driver_id),
    INDEX idx_status (status),
    FOREIGN KEY (driver_id)  REFERENCES drivers(driver_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id)          ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Seed default users (bcrypt-hashed; regenerate in production)
-- admin / admin123
-- fleet_manager / fleet123
-- Note: Real passwords are seeded by db_init.py at startup with live bcrypt hashing.
