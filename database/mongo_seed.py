"""
database/mongo_seed.py
Standalone MongoDB database seeder.
Connects to MongoDB (or mongomock if server not running) and seeds:
- Admin and fleet manager users
- 50 drivers
- 1000 trips with precalculated risk scores
"""
import os
import sys

# Ensure backend directory is in python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database.mongodb import initialize_mongodb, get_mongo_db

def main():
    print("=" * 60)
    print("  Driver Behavior Scoring System — MongoDB Seeder")
    print("=" * 60)
    initialize_mongodb()
    db = get_mongo_db()

    users_count = db.users.count_documents({})
    drivers_count = db.drivers.count_documents({})
    trips_count = db.trips.count_documents({})
    scores_count = db.scores.count_documents({})

    print(f"\nSeeding summary in MongoDB:")
    print(f"  • Users   : {users_count}")
    print(f"  • Drivers : {drivers_count}")
    print(f"  • Trips   : {trips_count}")
    print(f"  • Scores  : {scores_count}")
    print("\nMongoDB database is ready.")

if __name__ == "__main__":
    main()
