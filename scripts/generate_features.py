#!/usr/bin/env python3
"""
Manually generate features from historical bike station status and weather data
"""

import sys
from pathlib import Path
import pandas as pd
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db_context
from sqlalchemy import text
from datetime import datetime

logger.info("=" * 70)
logger.info("GENERATING FEATURES FROM HISTORICAL DATA")
logger.info("=" * 70)

# Fetch bike station status data
logger.info("Fetching bike station status data...")

with get_db_context() as db:
    status_df = pd.read_sql(
        text("""
            SELECT
                station_id,
                timestamp,
                bikes_available,
                docks_available
            FROM bike_station_status
            ORDER BY timestamp
        """),
        db.connection()
    )

logger.info(f"Loaded {len(status_df)} station status records")

# Fetch weather data
logger.info("Fetching weather data...")

with get_db_context() as db:
    weather_df = pd.read_sql(
        text("""
            SELECT
                timestamp,
                temperature,
                humidity,
                wind_speed,
                precipitation,
                weather_condition
            FROM weather_data
            ORDER BY timestamp
        """),
        db.connection()
    )

logger.info(f"Loaded {len(weather_df)} weather records")

# Merge bike status with weather (on hour)
logger.info("Merging bike status with weather data...")

status_df['hour'] = pd.to_datetime(status_df['timestamp']).dt.floor('h')
weather_df['hour'] = pd.to_datetime(weather_df['timestamp']).dt.floor('h')

merged = status_df.merge(
    weather_df[['hour', 'temperature', 'humidity', 'wind_speed', 'precipitation']],
    on='hour',
    how='left'
)

logger.info(f"Merged dataset has {len(merged)} records")

# Generate temporal features
logger.info("Generating temporal features...")

merged['timestamp'] = pd.to_datetime(merged['timestamp'])
merged['hour_of_day'] = merged['timestamp'].dt.hour
merged['day_of_week'] = merged['timestamp'].dt.dayofweek
merged['day_of_month'] = merged['timestamp'].dt.day
merged['month'] = merged['timestamp'].dt.month
merged['is_weekend'] = (merged['day_of_week'] >= 5).astype(int)

# Business hours feature
merged['is_business_hours'] = ((merged['hour_of_day'] >= 9) & (merged['hour_of_day'] <= 17)).astype(int)

# Rush hour features
merged['is_morning_rush'] = ((merged['hour_of_day'] >= 7) & (merged['hour_of_day'] <= 9)).astype(int)
merged['is_evening_rush'] = ((merged['hour_of_day'] >= 17) & (merged['hour_of_day'] <= 19)).astype(int)

# Generate lag features (1h, 6h, 24h)
logger.info("Generating lag features...")

merged = merged.sort_values(['station_id', 'timestamp'])

for lag_hours in [1, 6, 24]:
    merged[f'bikes_lag_{lag_hours}h'] = merged.groupby('station_id')['bikes_available'].shift(lag_hours)
    merged[f'docks_lag_{lag_hours}h'] = merged.groupby('station_id')['docks_available'].shift(lag_hours)

# Generate rolling features (3h, 6h windows)
logger.info("Generating rolling features...")

for window_hours in [3, 6]:
    merged[f'bikes_rolling_mean_{window_hours}h'] = merged.groupby('station_id')['bikes_available'] \
        .transform(lambda x: x.rolling(window=window_hours, min_periods=1).mean())

    merged[f'bikes_rolling_std_{window_hours}h'] = merged.groupby('station_id')['bikes_available'] \
        .transform(lambda x: x.rolling(window=window_hours, min_periods=1).std())

# Drop rows with NaN (from lag/rolling features)
logger.info("Cleaning data...")
original_len = len(merged)
merged = merged.dropna()
logger.info(f"Dropped {original_len - len(merged)} rows with NaN values")

# Limit to 10,000 features for faster training
merged = merged.head(10000)
logger.info(f"Limited to {len(merged)} feature records for training")

# Insert into features table
logger.info("Inserting features into database...")

with get_db_context() as db:
    inserted = 0

    for _, row in merged.iterrows():
        try:
            # Create feature JSON
            features_json = {
                'hour_of_day': int(row['hour_of_day']),
                'day_of_week': int(row['day_of_week']),
                'day_of_month': int(row['day_of_month']),
                'month': int(row['month']),
                'is_weekend': int(row['is_weekend']),
                'is_business_hours': int(row['is_business_hours']),
                'is_morning_rush': int(row['is_morning_rush']),
                'is_evening_rush': int(row['is_evening_rush']),
                'temperature': float(row['temperature']) if pd.notna(row['temperature']) else None,
                'humidity': float(row['humidity']) if pd.notna(row['humidity']) else None,
                'wind_speed': float(row['wind_speed']) if pd.notna(row['wind_speed']) else None,
                'precipitation': float(row['precipitation']) if pd.notna(row['precipitation']) else None,
                'bikes_available': int(row['bikes_available']),
                'docks_available': int(row['docks_available']),
                'bikes_lag_1h': float(row['bikes_lag_1h']),
                'bikes_lag_6h': float(row['bikes_lag_6h']),
                'bikes_lag_24h': float(row['bikes_lag_24h']),
                'docks_lag_1h': float(row['docks_lag_1h']),
                'docks_lag_6h': float(row['docks_lag_6h']),
                'docks_lag_24h': float(row['docks_lag_24h']),
                'bikes_rolling_mean_3h': float(row['bikes_rolling_mean_3h']),
                'bikes_rolling_std_3h': float(row['bikes_rolling_std_3h']),
                'bikes_rolling_mean_6h': float(row['bikes_rolling_mean_6h']),
                'bikes_rolling_std_6h': float(row['bikes_rolling_std_6h']),
            }

            import json
            db.execute(
                text("""
                    INSERT INTO features
                    (station_id, timestamp, feature_json, feature_version, created_at)
                    VALUES
                    (:station_id, :timestamp, CAST(:feature_json AS jsonb), :feature_version, NOW())
                    ON CONFLICT (station_id, timestamp, feature_version) DO NOTHING
                """),
                {
                    "station_id": str(row['station_id']),
                    "timestamp": row['timestamp'],
                    "feature_json": json.dumps(features_json),
                    "feature_version": "v1.0"
                }
            )
            inserted += 1

            if inserted % 1000 == 0:
                logger.info(f"Inserted {inserted} feature records...")
                db.commit()

        except Exception as e:
            logger.error(f"Failed to insert feature record: {e}")
            continue

    db.commit()
    logger.info(f"✓ Total inserted: {inserted} feature records")

# Verify
with get_db_context() as db:
    result = db.execute(
        text("""
            SELECT
                COUNT(*) as total,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(DISTINCT station_id) as unique_stations
            FROM features
        """)
    ).fetchone()

    logger.info("=" * 70)
    logger.info("FEATURES SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total feature records: {result[0]}")
    logger.info(f"Date range: {result[1]} to {result[2]}")
    logger.info(f"Unique stations: {result[3]}")

logger.success("✓ Feature generation complete!")
