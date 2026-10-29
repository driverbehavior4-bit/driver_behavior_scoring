"""
ml/preprocessing/pipeline.py
Preprocessing and feature engineering pipeline.
Pure Python + Pandas + NumPy (no sklearn).
"""
import os
import numpy as np
import pandas as pd

FEATURE_COLS = [
    "average_speed", "max_speed", "harsh_braking", "harsh_acceleration",
    "trip_duration", "speed_difference", "total_harsh_events",
    "harsh_events_per_minute", "speed_risk", "braking_risk", "acceleration_risk",
]


def load_raw_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    print(f"[load_raw_data] Loaded {df.shape[0]} rows x {df.shape[1]} cols from '{filepath}'")
    return df


def save_processed(df: pd.DataFrame, filepath: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"[save_processed] Saved {df.shape[0]} rows to '{filepath}'")


def load_processed(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    print(f"[load_processed] Loaded {df.shape[0]} rows from '{filepath}'")
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    before = len(df)
    df.drop_duplicates(subset=["trip_id"], keep="first", inplace=True)
    if len(df) < before:
        print(f"[preprocess] Removed {before - len(df)} duplicate trip_id rows")

    numeric = ["average_speed", "max_speed", "harsh_braking", "harsh_acceleration",
               "trip_duration", "distance", "idle_time"]
    for col in numeric:
        if col in df.columns:
            miss = df[col].isnull().sum()
            if miss:
                med = df[col].median()
                df[col] = df[col].fillna(med)
                print(f"[preprocess] Filled {miss} NaN in '{col}' with median {med:.2f}")

    df["average_speed"]      = df["average_speed"].clip(lower=0, upper=250)
    df["max_speed"]          = df["max_speed"].clip(lower=0, upper=300)
    df["harsh_braking"]      = df["harsh_braking"].clip(lower=0, upper=20)
    df["harsh_acceleration"] = df["harsh_acceleration"].clip(lower=0, upper=20)
    df["trip_duration"]      = df["trip_duration"].clip(lower=0.1)
    df["max_speed"]          = df[["max_speed", "average_speed"]].max(axis=1)

    print(f"[preprocess] Clean shape: {df.shape}")
    return df


def _clip(series, lo=0.0, hi=100.0):
    return series.clip(lower=lo, upper=hi)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["speed_difference"]        = df["max_speed"] - df["average_speed"]
    df["total_harsh_events"]      = df["harsh_braking"] + df["harsh_acceleration"]
    safe_dur                      = df["trip_duration"].replace(0, np.nan)
    df["harsh_events_per_minute"] = (df["total_harsh_events"] / safe_dur).fillna(0.0).round(4)
    df["speed_risk"]              = (df["max_speed"] > 100).astype(int)
    df["braking_risk"]            = (df["harsh_braking"] >= 4).astype(int)
    df["acceleration_risk"]       = (df["harsh_acceleration"] >= 4).astype(int)
    df["risk_indicator"]          = df["speed_risk"] + df["braking_risk"] + df["acceleration_risk"]

    df["speed_score"]        = _clip(100 - (df["max_speed"] - 80) * 2)
    df["braking_score"]      = _clip(100 - df["harsh_braking"] * 10)
    df["acceleration_score"] = _clip(100 - df["harsh_acceleration"] * 10)
    df["trip_safety_score"]  = (
        df["speed_score"] * 0.4 + df["braking_score"] * 0.3 + df["acceleration_score"] * 0.3
    ).round(2)

    # risk_label for ML: 0=Low (>=70), 1=Moderate (>=40), 2=High (<40)
    conditions = [df["trip_safety_score"] >= 70, df["trip_safety_score"] >= 40]
    df["risk_label"] = np.select(conditions, [0, 1], default=2).astype(int)

    dist = df["risk_label"].value_counts().sort_index()
    print(f"[engineer_features] Risk label distribution:\n{dist.to_string()}")
    print(f"[engineer_features] Output shape: {df.shape}")
    return df


def prepare_training_data(df: pd.DataFrame):
    X = df[FEATURE_COLS].to_numpy(dtype=float)
    y = df["risk_label"].to_numpy(dtype=int)
    print(f"[prepare_training_data] X: {X.shape}")
    return X, y, FEATURE_COLS
