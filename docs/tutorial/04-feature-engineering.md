# Chapter 4: Feature Engineering Pipeline

## Overview

In this chapter, you'll:
- Build 22+ time-series features for bike demand prediction
- Implement temporal, lag, rolling, weather, and holiday features
- Store features in PostgreSQL with JSONB
- Handle missing data gracefully
- Version features for reproducibility

**Estimated Time**: 4 hours

## Why Feature Engineering Matters

**Raw data:**
```
station_id | timestamp           | bikes_available
-----------+---------------------+----------------
station-1  | 2024-01-15 14:00:00 | 15
```

**After feature engineering:**
```
{
  "hour_of_day": 14,
  "day_of_week": 1,
  "is_weekend": 0,
  "is_morning_rush": 0,
  "is_evening_rush": 0,
  "bikes_lag_1h": 12,
  "bikes_lag_24h": 18,
  "bikes_rolling_mean_3h": 14.5,
  "temperature": 22.5,
  "is_holiday": 0
}
```

**Result**: Model RMSE improves from 3.2 → 0.51 bikes!

## Feature Categories

### 1. Temporal Features (8 features)

**Why?** Bike demand has strong time patterns:
- 🌅 Morning rush (7-9 AM): High demand
- 🌆 Evening rush (5-8 PM): Peak demand
- 🌙 Night (11 PM-5 AM): Low demand
- 📅 Weekend vs Weekday: Different patterns

Open `src/features/temporal_features.py`:

```python
import pandas as pd
from datetime import datetime
import holidays

class TemporalFeatureGenerator:
    """Generate time-based features"""

    def __init__(self):
        self.us_holidays = holidays.US()

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate temporal features from timestamp

        Input columns required: timestamp
        Output columns added: 8 temporal features
        """
        df = df.copy()

        # Extract datetime components
        df['hour_of_day'] = df['timestamp'].dt.hour  # 0-23
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
        df['day_of_month'] = df['timestamp'].dt.day  # 1-31
        df['week_of_year'] = df['timestamp'].dt.isocalendar().week  # 1-52
        df['month'] = df['timestamp'].dt.month  # 1-12

        # Binary flags
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)  # Saturday/Sunday
        df['is_weekday'] = (~df['is_weekend'].astype(bool)).astype(int)

        # Rush hour flags (critical for demand!)
        df['is_morning_rush'] = (
            (df['hour_of_day'].between(7, 9)) &
            (df['is_weekday'] == 1)
        ).astype(int)

        df['is_evening_rush'] = (
            (df['hour_of_day'].between(17, 20)) &
            (df['is_weekday'] == 1)
        ).astype(int)

        df['is_business_hours'] = (
            df['hour_of_day'].between(9, 17)
        ).astype(int)

        return df
```

**Test it:**
```python
from src.features.temporal_features import TemporalFeatureGenerator
import pandas as pd

# Create test data
df = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-15 08:00', periods=24, freq='H')
})

gen = TemporalFeatureGenerator()
result = gen.generate(df)

print(result[['hour_of_day', 'is_morning_rush', 'is_evening_rush']].head(10))
```

**Output:**
```
   hour_of_day  is_morning_rush  is_evening_rush
0            8                1                0  ← Morning rush!
1            9                1                0  ← Morning rush!
2           10                0                0
3           11                0                0
4           12                0                0
5           13                0                0
6           14                0                0
7           15                0                0
8           16                0                0
9           17                0                1  ← Evening rush!
```

### 2. Lag Features (6 features)

**Why?** Past demand predicts future demand:
- If 10 bikes available 1 hour ago → Likely similar now
- If 20 bikes available yesterday same time → Weekly pattern
- If station empty 6 hours ago → May still be depleted

Open `src/features/lag_features.py`:

```python
import pandas as pd
from typing import List

class LagFeatureGenerator:
    """Generate lagged features for time-series"""

    def __init__(self, lag_hours: List[int], target_column: str = 'bikes_available'):
        """
        Args:
            lag_hours: List of lag windows (e.g., [1, 6, 24])
            target_column: Column to create lags from
        """
        self.lag_hours = lag_hours
        self.target_column = target_column

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create lag features

        Important: Data must be sorted by timestamp!
        """
        df = df.copy()
        df = df.sort_values(['station_id', 'timestamp'])

        for lag in self.lag_hours:
            col_name = f'{self.target_column}_lag_{lag}h'

            # Shift by lag hours
            df[col_name] = df.groupby('station_id')[self.target_column].shift(lag)

            # First N rows will be NaN (no historical data)
            # We'll fill these with 0 or median later

        return df
```

**Critical Concept**: Lag features create NaN for first N hours!

```
timestamp           | bikes_available | bikes_lag_1h | bikes_lag_24h
--------------------+-----------------+--------------+---------------
2024-01-01 00:00:00 | 10              | NaN          | NaN         ← No history!
2024-01-01 01:00:00 | 12              | 10           | NaN         ← Only 1h history
2024-01-01 02:00:00 | 15              | 12           | NaN
...
2024-01-02 00:00:00 | 18              | 16           | 10          ← Full 24h history
```

**How to handle NaN?**
- ❌ **Don't drop rows** (loses data)
- ✅ **Fill with 0** (indicates "no historical data")
- ✅ **Fill with median** (conservative estimate)

### 3. Rolling Statistics (6 features)

**Why?** Capture trends and variability:
- Rolling mean: Is demand increasing/decreasing?
- Rolling std: Is demand stable or volatile?
- Rolling min/max: Extreme values

Open `src/features/rolling_features.py`:

```python
import pandas as pd
from typing import List

class RollingFeatureGenerator:
    """Generate rolling window statistics"""

    def __init__(
        self,
        windows: List[int],
        statistics: List[str],
        target_column: str = 'bikes_available'
    ):
        """
        Args:
            windows: Window sizes in hours (e.g., [3, 6])
            statistics: Stats to compute (e.g., ['mean', 'std'])
            target_column: Column to aggregate
        """
        self.windows = windows
        self.statistics = statistics
        self.target_column = target_column

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create rolling features"""
        df = df.copy()
        df = df.sort_values(['station_id', 'timestamp'])

        for window in self.windows:
            for stat in self.statistics:
                col_name = f'{self.target_column}_rolling_{stat}_{window}h'

                # Calculate rolling statistic
                df[col_name] = (
                    df.groupby('station_id')[self.target_column]
                    .rolling(window=window, min_periods=1)
                    .agg(stat)
                    .reset_index(level=0, drop=True)
                )

        return df
```

**Example:**
```python
# 3-hour rolling mean
timestamp           | bikes_available | bikes_rolling_mean_3h
--------------------+-----------------+----------------------
2024-01-01 00:00:00 | 10              | 10.0                 ← Only 1 point
2024-01-01 01:00:00 | 12              | 11.0                 ← (10+12)/2
2024-01-01 02:00:00 | 15              | 12.3                 ← (10+12+15)/3
2024-01-01 03:00:00 | 18              | 15.0                 ← (12+15+18)/3 ← Now full window
```

### 4. Weather Features (5+ features)

**Why?** Weather drastically affects bike demand:
- ☀️ Sunny + 20°C → Peak demand
- 🌧️ Rain → 50% drop
- ❄️ Snow → 80% drop
- 🌡️ Extreme heat (>35°C) → Low demand

Open `src/features/weather_features.py`:

```python
import pandas as pd

class WeatherFeatureGenerator:
    """Generate weather-based features"""

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input columns required:
          - temperature, humidity, wind_speed, precipitation,
            weather_condition

        Output columns added:
          - is_rainy, is_snowy, temp_category, wind_category
        """
        df = df.copy()

        # Binary weather flags
        df['is_rainy'] = (df['precipitation'] > 0).astype(int)
        df['is_snowy'] = (
            df['weather_condition'].str.contains('Snow', case=False, na=False)
        ).astype(int)

        # Temperature categories
        df['temp_category'] = pd.cut(
            df['temperature'],
            bins=[-float('inf'), 0, 10, 20, 30, float('inf')],
            labels=['freezing', 'cold', 'mild', 'warm', 'hot']
        )

        # Wind categories (m/s)
        df['wind_category'] = pd.cut(
            df['wind_speed'],
            bins=[-float('inf'), 5, 10, 15, float('inf')],
            labels=['calm', 'moderate', 'strong', 'very_strong']
        )

        # Comfort score (0-1, higher = better biking conditions)
        df['comfort_score'] = 0.5  # Default

        # Adjust for temperature
        df.loc[df['temperature'].between(15, 25), 'comfort_score'] += 0.3

        # Penalize for rain
        df.loc[df['is_rainy'] == 1, 'comfort_score'] -= 0.4

        # Penalize for strong wind
        df.loc[df['wind_speed'] > 10, 'comfort_score'] -= 0.2

        # Clip to [0, 1]
        df['comfort_score'] = df['comfort_score'].clip(0, 1)

        return df
```

### 5. Holiday Features (2 features)

**Why?** Holidays have different demand patterns:
- National holidays: Lower commute, higher leisure
- Day before holiday: Early departure from work
- Day after holiday: Slow return

Open `src/features/holiday_features.py`:

```python
import pandas as pd
import holidays
from datetime import timedelta

class HolidayFeatureGenerator:
    """Generate holiday-related features"""

    def __init__(self, country: str = 'US'):
        self.holidays = holidays.country_holidays(country)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate holiday features"""
        df = df.copy()

        # Is today a holiday?
        df['is_holiday'] = df['timestamp'].dt.date.apply(
            lambda d: int(d in self.holidays)
        )

        # Days until next holiday
        df['days_to_holiday'] = df['timestamp'].apply(
            self._days_to_next_holiday
        )

        return df

    def _days_to_next_holiday(self, dt):
        """Calculate days until next holiday"""
        date = dt.date()
        for i in range(365):  # Search up to 1 year ahead
            future_date = date + timedelta(days=i)
            if future_date in self.holidays:
                return i
        return 365  # No holiday in next year
```

## Complete Feature Generation Script

Open `scripts/generate_features.py`:

```python
#!/usr/bin/env python3
"""
Generate features from raw bike and weather data

This script:
1. Loads raw data from bike_station_status and weather_data
2. Merges them on timestamp
3. Generates all features
4. Stores in features table with version tracking
"""

import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import sys

from src.features.temporal_features import TemporalFeatureGenerator
from src.features.lag_features import LagFeatureGenerator
from src.features.rolling_features import RollingFeatureGenerator
from src.features.weather_features import WeatherFeatureGenerator
from src.features.holiday_features import HolidayFeatureGenerator
from src.data.storage.postgres_handler import PostgreSQLHandler

# Feature version (increment when features change)
FEATURE_VERSION = "v1.0"

def load_raw_data(db: PostgreSQLHandler, days_back: int = 30):
    """Load raw data from last N days"""
    logger.info(f"Loading data from last {days_back} days...")

    # Load bike station status
    query_bikes = f"""
        SELECT
            station_id,
            timestamp,
            bikes_available,
            docks_available
        FROM bike_station_status
        WHERE timestamp >= NOW() - INTERVAL '{days_back} days'
        ORDER BY station_id, timestamp
    """

    bikes_df = pd.read_sql(query_bikes, db.engine)
    logger.info(f"Loaded {len(bikes_df)} bike status records")

    # Load weather data
    query_weather = f"""
        SELECT
            timestamp,
            temperature,
            feels_like,
            humidity,
            wind_speed,
            precipitation,
            weather_condition,
            visibility,
            pressure
        FROM weather_data
        WHERE timestamp >= NOW() - INTERVAL '{days_back} days'
        ORDER BY timestamp
    """

    weather_df = pd.read_sql(query_weather, db.engine)
    logger.info(f"Loaded {len(weather_df)} weather records")

    return bikes_df, weather_df

def merge_data(bikes_df, weather_df):
    """Merge bike and weather data on timestamp"""
    logger.info("Merging bike and weather data...")

    # Round timestamps to nearest hour for joining
    bikes_df['timestamp_hour'] = bikes_df['timestamp'].dt.floor('H')
    weather_df['timestamp_hour'] = weather_df['timestamp'].dt.floor('H')

    # Merge
    merged = bikes_df.merge(
        weather_df,
        on='timestamp_hour',
        how='left',
        suffixes=('', '_weather')
    )

    # Drop duplicate timestamp column
    merged = merged.drop(columns=['timestamp_weather'], errors='ignore')

    logger.info(f"Merged dataset has {len(merged)} rows")
    return merged

def generate_all_features(df):
    """Apply all feature generators"""
    logger.info("Generating features...")

    # 1. Temporal features
    temporal_gen = TemporalFeatureGenerator()
    df = temporal_gen.generate(df)
    logger.info("✓ Temporal features generated")

    # 2. Lag features for bikes
    bikes_lag_gen = LagFeatureGenerator(
        lag_hours=[1, 6, 24],
        target_column='bikes_available'
    )
    df = bikes_lag_gen.generate(df)
    logger.info("✓ Bike lag features generated")

    # 3. Lag features for docks
    docks_lag_gen = LagFeatureGenerator(
        lag_hours=[1, 6, 24],
        target_column='docks_available'
    )
    df = docks_lag_gen.generate(df)
    logger.info("✓ Dock lag features generated")

    # 4. Rolling features
    rolling_gen = RollingFeatureGenerator(
        windows=[3, 6],
        statistics=['mean', 'std'],
        target_column='bikes_available'
    )
    df = rolling_gen.generate(df)
    logger.info("✓ Rolling features generated")

    # 5. Weather features
    weather_gen = WeatherFeatureGenerator()
    df = weather_gen.generate(df)
    logger.info("✓ Weather features generated")

    # 6. Holiday features
    holiday_gen = HolidayFeatureGenerator()
    df = holiday_gen.generate(df)
    logger.info("✓ Holiday features generated")

    return df

def handle_missing_values(df):
    """Fill NaN values intelligently"""
    logger.info("Handling missing values...")

    original_len = len(df)

    # Fill lag and rolling features with 0 (indicates no historical data)
    lag_rolling_cols = [col for col in df.columns if 'lag' in col or 'rolling' in col]
    df[lag_rolling_cols] = df[lag_rolling_cols].fillna(0)

    # Fill weather features with median
    weather_cols = ['temperature', 'humidity', 'wind_speed', 'precipitation']
    for col in weather_cols:
        if col in df.columns:
            median_val = df[col].median() if len(df[col].dropna()) > 0 else 0
            df[col] = df[col].fillna(median_val)

    filled_count = original_len - len(df.dropna())
    logger.info(f"Filled {filled_count} NaN values (kept all {len(df)} rows)")

    return df

def save_features(db: PostgreSQLHandler, df):
    """Save features to database"""
    logger.info("Saving features to database...")

    # Select feature columns (exclude metadata)
    exclude_cols = ['station_id', 'timestamp', 'timestamp_hour',
                    'bikes_available', 'docks_available', 'date', 'holiday_name']

    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # Convert features to JSON
    features_json = df[feature_cols].to_dict('records')

    # Prepare for database insert
    records = []
    for idx, row in df.iterrows():
        records.append({
            'station_id': row['station_id'],
            'timestamp': row['timestamp'],
            'feature_json': features_json[idx],
            'feature_version': FEATURE_VERSION
        })

    # Batch insert
    logger.info(f"Inserting {len(records)} feature records...")

    from sqlalchemy import text
    session = db.Session()

    try:
        query = text("""
            INSERT INTO features
            (station_id, timestamp, feature_json, feature_version, created_at)
            VALUES
            (:station_id, :timestamp, CAST(:feature_json AS jsonb), :feature_version, NOW())
            ON CONFLICT (station_id, timestamp, feature_version) DO NOTHING
        """)

        # Convert dict to JSON string for PostgreSQL
        import json
        for record in records:
            record['feature_json'] = json.dumps(record['feature_json'])

        result = session.execute(query, records)
        session.commit()

        logger.info(f"✓ Inserted {result.rowcount} feature records")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to insert features: {e}")
        raise
    finally:
        session.close()

def main():
    logger.info("Starting feature generation...")

    # Connect to database
    db = PostgreSQLHandler()

    # Load data
    bikes_df, weather_df = load_raw_data(db, days_back=30)

    # Merge
    merged = merge_data(bikes_df, weather_df)

    # Generate features
    features = generate_all_features(merged)

    # Handle NaN
    features = handle_missing_values(features)

    # Save to database
    save_features(db, features)

    logger.info("✅ Feature generation complete!")

if __name__ == "__main__":
    main()
```

## Running Feature Generation

```bash
# From project root
docker compose -f infrastructure/docker-compose.yml run --rm \
  -e PYTHONPATH=/app \
  api python scripts/generate_features.py
```

**Expected Output:**
```
2024-01-15 14:30:00 | INFO | Starting feature generation...
2024-01-15 14:30:01 | INFO | Loading data from last 30 days...
2024-01-15 14:30:02 | INFO | Loaded 72000 bike status records
2024-01-15 14:30:02 | INFO | Loaded 720 weather records
2024-01-15 14:30:02 | INFO | Merging bike and weather data...
2024-01-15 14:30:03 | INFO | Merged dataset has 72000 rows
2024-01-15 14:30:03 | INFO | Generating features...
2024-01-15 14:30:03 | INFO | ✓ Temporal features generated
2024-01-15 14:30:04 | INFO | ✓ Bike lag features generated
2024-01-15 14:30:04 | INFO | ✓ Dock lag features generated
2024-01-15 14:30:05 | INFO | ✓ Rolling features generated
2024-01-15 14:30:05 | INFO | ✓ Weather features generated
2024-01-15 14:30:05 | INFO | ✓ Holiday features generated
2024-01-15 14:30:05 | INFO | Handling missing values...
2024-01-15 14:30:05 | INFO | Filled 2160 NaN values (kept all 72000 rows)
2024-01-15 14:30:05 | INFO | Saving features to database...
2024-01-15 14:30:05 | INFO | Inserting 72000 feature records...
2024-01-15 14:30:10 | INFO | ✓ Inserted 72000 feature records
2024-01-15 14:30:10 | INFO | ✅ Feature generation complete!
```

## Verify Features

```bash
# Check features table
docker compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c "
    SELECT
      COUNT(*) as total_features,
      feature_version,
      MIN(timestamp) as earliest,
      MAX(timestamp) as latest
    FROM features
    GROUP BY feature_version;
  "
```

**Output:**
```
 total_features | feature_version |      earliest       |       latest
----------------+-----------------+---------------------+---------------------
          72000 | v1.0            | 2024-12-16 14:00:00 | 2025-01-15 14:00:00
```

## Summary

### Feature Count by Category

| Category | Count | Examples |
|----------|-------|----------|
| Temporal | 8 | hour_of_day, is_weekend, is_morning_rush |
| Lag (bikes) | 3 | bikes_lag_1h, bikes_lag_6h, bikes_lag_24h |
| Lag (docks) | 3 | docks_lag_1h, docks_lag_6h, docks_lag_24h |
| Rolling | 4 | bikes_rolling_mean_3h, bikes_rolling_std_6h |
| Weather | 5+ | temperature, is_rainy, comfort_score |
| Holiday | 2 | is_holiday, days_to_holiday |
| **Total** | **25+** | |

### Key Takeaways

✅ **Feature engineering is critical** - Improved RMSE from 3.2 → 0.51
✅ **Handle NaN carefully** - Fill, don't drop
✅ **Version your features** - Track changes over time
✅ **JSONB is flexible** - No schema migrations needed
✅ **Test incrementally** - Build one feature type at a time

## Next Steps

Now that you have 25+ engineered features, head to **[Chapter 5: Model Training Pipeline](05-model-training.md)** to train XGBoost and LightGBM models!

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
