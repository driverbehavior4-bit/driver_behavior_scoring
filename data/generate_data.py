"""
data/generate_data.py
Generates 1000 synthetic telematics trip records.
Driver profiles:
  D001-D010  aggressive (high speeds, many harsh events)
  D011-D025  moderate
  D026-D050  safe
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SEED = 42
N_TRIPS = 1000
N_DRIVERS = 50
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "raw", "driving_data.csv")


def generate_dataset(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    today = datetime.today().date()

    rows = []
    trip_counter = 1

    # Distribute trips across drivers
    trips_per_driver = N_TRIPS // N_DRIVERS  # 20 each

    first_names = ["James","Mary","John","Patricia","Robert","Jennifer","Michael",
                   "Linda","William","Barbara","David","Susan","Richard","Jessica",
                   "Joseph","Sarah","Thomas","Karen","Charles","Lisa","Christopher",
                   "Nancy","Daniel","Betty","Matthew","Margaret","Anthony","Sandra",
                   "Donald","Ashley","Mark","Dorothy","Paul","Kimberly","Steven",
                   "Emily","George","Donna","Kenneth","Michelle","Andrew","Carol",
                   "Joshua","Amanda","Kevin","Melissa","Brian","Deborah","Edward","Stephanie"]
    last_names  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
                   "Davis","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
                   "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
                   "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker"]

    rng2 = np.random.default_rng(seed + 1)
    driver_names = {
        f"D{i:03d}": f"{rng2.choice(first_names)} {rng2.choice(last_names)}"
        for i in range(1, N_DRIVERS + 1)
    }

    for i in range(1, N_DRIVERS + 1):
        driver_id = f"D{i:03d}"
        n_trips = trips_per_driver + (1 if i <= N_TRIPS % N_DRIVERS else 0)

        if i <= 10:          # aggressive
            speed_range   = (85, 130)
            braking_range = (4, 10)
            accel_range   = (4, 10)
            dur_range     = (10, 80)
        elif i <= 25:        # moderate
            speed_range   = (55, 100)
            braking_range = (1, 6)
            accel_range   = (1, 6)
            dur_range     = (10, 100)
        else:                # safe
            speed_range   = (35, 80)
            braking_range = (0, 3)
            accel_range   = (0, 3)
            dur_range     = (5, 120)

        for _ in range(n_trips):
            trip_id     = f"T{trip_counter:05d}"
            trip_counter += 1
            days_ago    = int(rng.integers(0, 181))
            trip_date   = (today - timedelta(days=days_ago)).isoformat()
            avg_speed   = round(float(rng.uniform(*speed_range)), 2)
            speed_delta = round(float(rng.uniform(5, 50)), 2)
            max_speed   = round(avg_speed + speed_delta, 2)
            harsh_brk   = int(rng.integers(braking_range[0], braking_range[1] + 1))
            harsh_acc   = int(rng.integers(accel_range[0],   accel_range[1]   + 1))
            duration    = round(float(rng.uniform(*dur_range)), 2)
            distance    = round(duration * avg_speed / 60, 2)
            idle_time   = round(float(rng.uniform(0, 20)), 2)

            rows.append({
                "driver_id":           driver_id,
                "driver_name":         driver_names[driver_id],
                "trip_id":             trip_id,
                "trip_date":           trip_date,
                "average_speed":       avg_speed,
                "max_speed":           max_speed,
                "harsh_braking":       harsh_brk,
                "harsh_acceleration":  harsh_acc,
                "trip_duration":       duration,
                "distance":            distance,
                "idle_time":           idle_time,
            })

    df = pd.DataFrame(rows)
    # Shuffle rows
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main():
    print("=" * 55)
    print("  Driver Behavior Dataset Generator")
    print("=" * 55)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df = generate_dataset()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} cols")
    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))
    print("\nMissing values:")
    print(df.isnull().sum().to_string())
    print("\nDriver risk distribution (by avg trip score):")
    # Quick score preview
    df["_spd_score"] = (100 - (df["max_speed"] - 80) * 2).clip(0, 100)
    df["_brk_score"] = (100 - df["harsh_braking"] * 10).clip(0, 100)
    df["_acc_score"] = (100 - df["harsh_acceleration"] * 10).clip(0, 100)
    df["_score"] = df["_spd_score"] * 0.4 + df["_brk_score"] * 0.3 + df["_acc_score"] * 0.3
    driver_avg = df.groupby("driver_id")["_score"].mean()
    high_risk = (driver_avg < 40).sum()
    moderate  = ((driver_avg >= 40) & (driver_avg < 70)).sum()
    low_risk  = (driver_avg >= 70).sum()
    print(f"  High-risk drivers  : {high_risk}")
    print(f"  Moderate drivers   : {moderate}")
    print(f"  Low-risk drivers   : {low_risk}")


if __name__ == "__main__":
    main()
