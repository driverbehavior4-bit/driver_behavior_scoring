/**
 * database/mongo_init.js
 * MongoDB initialization script for Driver Behavior Scoring System.
 *
 * Usage with mongosh:
 *   mongosh "mongodb://localhost:27017/driver_safety" database/mongo_init.js
 *
 * Or in Docker:
 *   Place in /docker-entrypoint-initdb.d/
 */

db = db.getSiblingDB("driver_safety");

print("--- Initializing driver_safety MongoDB Database ---");

// 1. Users collection & indexes
db.createCollection("users");
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });

// 2. Drivers collection & indexes
db.createCollection("drivers");
db.drivers.createIndex({ driver_id: 1 }, { unique: true });
db.drivers.createIndex({ name: 1 });

// 3. Trips collection & indexes
db.createCollection("trips");
db.trips.createIndex({ trip_id: 1 }, { unique: true });
db.trips.createIndex({ driver_id: 1 });
db.trips.createIndex({ trip_date: -1 });

// 4. Scores collection & indexes
db.createCollection("scores");
db.scores.createIndex({ trip_id: 1 }, { unique: true });
db.scores.createIndex({ driver_id: 1 });
db.scores.createIndex({ trip_safety_score: 1 });
db.scores.createIndex({ is_high_risk: 1 });

// 5. Coaching actions collection & indexes
db.createCollection("coaching_actions");
db.coaching_actions.createIndex({ id: 1 }, { unique: true });
db.coaching_actions.createIndex({ driver_id: 1 });
db.coaching_actions.createIndex({ status: 1 });

print("--- Collections and indexes created successfully in driver_safety ---");
