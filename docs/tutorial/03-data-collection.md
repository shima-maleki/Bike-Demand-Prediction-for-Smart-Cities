# Chapter 3: Data Collection Pipeline

## Overview

In this chapter, you'll:
- Understand the NYC Citi Bike API
- Collect historical bike station data
- Fetch weather data from OpenWeatherMap
- Store data in PostgreSQL
- Validate data quality

**Estimated Time**: 3 hours

## Data Sources

### 1. NYC Citi Bike System Data (GBFS)

**What is GBFS?**
- **G**eneral **B**ikeshare **F**eed **S**pecification
- Real-time JSON feeds for bike-sharing systems
- Used by 500+ cities worldwide
- Free and open (no API key needed)

**NYC Citi Bike Endpoints:**
```bash
# Station information (static data)
https://gbfs.citibikenyc.com/gbfs/en/station_information.json

# Station status (real-time data)
https://gbfs.citibikenyc.com/gbfs/en/station_status.json
```

**Sample Response (station_status.json):**
```json
{
  "last_updated": 1703700000,
  "data": {
    "stations": [
      {
        "station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c",
        "num_bikes_available": 15,
        "num_docks_available": 12,
        "num_bikes_disabled": 2,
        "num_docks_disabled": 1,
        "is_installed": 1,
        "is_renting": 1,
        "is_returning": 1,
        "last_reported": 1703700000
      }
    ]
  }
}
```

### 2. OpenWeatherMap API

**Why Weather Data?**
Weather significantly affects bike demand:
- ☀️ Sunny days → High demand
- 🌧️ Rainy days → Low demand
- ❄️ Cold/Snow → Very low demand
- 🌡️ Comfortable temperature (15-25°C) → Peak demand

**API Endpoint:**
```bash
https://api.openweathermap.org/data/2.5/weather?q=NewYork&appid=YOUR_API_KEY
```

**Get Free API Key:**
1. Go to [openweathermap.org/api](https://openweathermap.org/api)
2. Sign up (free tier: 1000 calls/day)
3. Get API key from dashboard
4. Add to `.env` file

## Data Collection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Collection Flow                     │
└─────────────────────────────────────────────────────────────┘

   ┌──────────────┐         ┌──────────────┐
   │  Citi Bike   │         │ OpenWeather  │
   │     API      │         │     API      │
   └──────┬───────┘         └──────┬───────┘
          │                        │
          │ HTTP GET              │ HTTP GET
          │                        │
          ▼                        ▼
   ┌─────────────────────────────────────┐
   │     Data Collectors (Python)        │
   │  - CitiBikeCollector                │
   │  - WeatherCollector                 │
   └──────────┬──────────────────────────┘
              │
              │ Validate & Clean
              │
              ▼
   ┌─────────────────────────────────────┐
   │      Data Processors                │
   │  - Great Expectations validation    │
   │  - Type checking                    │
   │  - Duplicate detection              │
   └──────────┬──────────────────────────┘
              │
              │ Insert/Upsert
              │
              ▼
   ┌─────────────────────────────────────┐
   │      PostgreSQL Database            │
   │  - bike_stations                    │
   │  - bike_station_status              │
   │  - weather_data                     │
   └─────────────────────────────────────┘
```

## Implementation: Citi Bike Collector

### Step 1: Understanding the Code

Open `src/data/collectors/citi_bike_collector.py`:

```python
import requests
from typing import List, Dict
from loguru import logger
from datetime import datetime

class CitiBikeCollector:
    """Collects data from NYC Citi Bike GBFS API"""

    # Base URL for NYC Citi Bike GBFS feeds
    BASE_URL = "https://gbfs.citibikenyc.com/gbfs/en"

    def __init__(self):
        self.session = requests.Session()  # Reuse TCP connections
        self.session.headers.update({
            'User-Agent': 'BikeDemanddPredictor/1.0'
        })

    def fetch_station_information(self) -> List[Dict]:
        """
        Fetch static station data (location, capacity, name)
        Updates infrequently (daily or less)
        """
        url = f"{self.BASE_URL}/station_information.json"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()  # Raise exception for 4xx/5xx

            data = response.json()
            stations = data['data']['stations']

            logger.info(f"Fetched {len(stations)} station records")
            return stations

        except requests.RequestException as e:
            logger.error(f"Failed to fetch station info: {e}")
            raise

    def fetch_station_status(self) -> List[Dict]:
        """
        Fetch real-time station status (bikes available, docks available)
        Updates every minute
        """
        url = f"{self.BASE_URL}/station_status.json"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            stations = data['data']['stations']

            logger.info(f"Fetched status for {len(stations)} stations")
            return stations

        except requests.RequestException as e:
            logger.error(f"Failed to fetch station status: {e}")
            raise
```

**Key Concepts:**

1. **Session Reuse**: `requests.Session()` reuses TCP connections (faster)
2. **Timeout**: Always set timeout (default is infinite!)
3. **Error Handling**: Use try/except for network failures
4. **Logging**: Track what's happening for debugging

### Step 2: Test the Collector

Create a test script to verify the collector works:

```bash
# Create test file
cat > test_collector.py << 'EOF'
from src.data.collectors.citi_bike_collector import CitiBikeCollector

collector = CitiBikeCollector()

# Test station information
stations = collector.fetch_station_information()
print(f"✅ Fetched {len(stations)} stations")
print(f"Sample station: {stations[0]}")

# Test station status
statuses = collector.fetch_station_status()
print(f"✅ Fetched status for {len(statuses)} stations")
print(f"Sample status: {statuses[0]}")
EOF

# Run test
python test_collector.py
```

**Expected Output:**
```
✅ Fetched 1879 stations
Sample station: {
  'station_id': '66db237e-0aca-11e7-82f6-3863bb44ef7c',
  'name': 'Central Park S & 6 Ave',
  'lat': 40.76590936,
  'lon': -73.97634151,
  'capacity': 39
}
✅ Fetched status for 1879 stations
Sample status: {
  'station_id': '66db237e-0aca-11e7-82f6-3863bb44ef7c',
  'num_bikes_available': 15,
  'num_docks_available': 12,
  'last_reported': 1703700000
}
```

## Implementation: Weather Collector

### Step 1: Understanding Weather Data

Open `src/data/collectors/weather_collector.py`:

```python
import requests
from typing import Dict, Optional
from loguru import logger
from datetime import datetime
import os

class WeatherCollector:
    """Collects weather data from OpenWeatherMap API"""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Weather API key required. "
                "Set WEATHER_API_KEY env variable or pass to constructor"
            )

        self.session = requests.Session()

    def fetch_current_weather(
        self,
        city: str = "New York",
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict:
        """
        Fetch current weather data

        Args:
            city: City name (used if lat/lon not provided)
            lat: Latitude (more accurate than city name)
            lon: Longitude

        Returns:
            Weather data dictionary
        """
        # Build query parameters
        params = {
            'appid': self.api_key,
            'units': 'metric'  # Celsius, m/s
        }

        # Use coordinates if provided (more accurate)
        if lat and lon:
            params['lat'] = lat
            params['lon'] = lon
        else:
            params['q'] = city

        url = f"{self.BASE_URL}/weather"

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract relevant fields
            weather = {
                'timestamp': datetime.utcnow(),
                'latitude': data['coord']['lat'],
                'longitude': data['coord']['lon'],
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'],
                'weather_condition': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description'],
                'visibility': data.get('visibility', 10000),
                'precipitation': data.get('rain', {}).get('1h', 0)
            }

            logger.info(
                f"Fetched weather: {weather['temperature']}°C, "
                f"{weather['weather_condition']}"
            )

            return weather

        except requests.RequestException as e:
            logger.error(f"Failed to fetch weather: {e}")
            raise
```

**Key Features:**

1. **Coordinate-based**: More accurate than city name
2. **Metric units**: Celsius, m/s (convert to imperial if needed)
3. **Handle missing data**: `data.get('visibility', 10000)` provides default
4. **Extract only needed fields**: Don't store everything

### Step 2: Test Weather Collector

```bash
# Test weather collector
cat > test_weather.py << 'EOF'
from src.data.collectors.weather_collector import WeatherCollector
import os

# Use your API key
api_key = os.getenv("WEATHER_API_KEY", "YOUR_KEY_HERE")
collector = WeatherCollector(api_key=api_key)

# Fetch weather for NYC (Citi Bike area)
weather = collector.fetch_current_weather(
    lat=40.7589,  # Times Square coordinates
    lon=-73.9851
)

print("✅ Weather data fetched:")
print(f"  Temperature: {weather['temperature']}°C")
print(f"  Feels like: {weather['feels_like']}°C")
print(f"  Humidity: {weather['humidity']}%")
print(f"  Conditions: {weather['weather_condition']}")
print(f"  Wind speed: {weather['wind_speed']} m/s")
EOF

python test_weather.py
```

## Storing Data in PostgreSQL

### Step 1: Understanding the Storage Handler

Open `src/data/storage/postgres_handler.py`:

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict
from loguru import logger
from datetime import datetime

class PostgreSQLHandler:
    """Handles PostgreSQL database operations"""

    def __init__(self, connection_string: str = None):
        if not connection_string:
            # Build from environment variables
            import os
            connection_string = (
                f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                f"{os.getenv('DB_PASSWORD', 'postgres')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_DATABASE', 'bike_demand_db')}"
            )

        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def insert_stations(self, stations: List[Dict]) -> int:
        """
        Insert or update bike stations
        Uses ON CONFLICT to handle duplicates
        """
        query = text("""
            INSERT INTO bike_stations (
                station_id, name, latitude, longitude, capacity, is_active
            ) VALUES (
                :station_id, :name, :lat, :lon, :capacity, TRUE
            )
            ON CONFLICT (station_id) DO UPDATE SET
                name = EXCLUDED.name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                capacity = EXCLUDED.capacity,
                updated_at = CURRENT_TIMESTAMP
        """)

        session = self.Session()
        try:
            result = session.execute(
                query,
                [
                    {
                        'station_id': s['station_id'],
                        'name': s['name'],
                        'lat': s['lat'],
                        'lon': s['lon'],
                        'capacity': s['capacity']
                    }
                    for s in stations
                ]
            )
            session.commit()
            count = result.rowcount
            logger.info(f"Inserted/updated {count} stations")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert stations: {e}")
            raise
        finally:
            session.close()

    def insert_station_status(self, statuses: List[Dict]) -> int:
        """
        Insert station status records
        Time-series data - always insert, never update
        """
        query = text("""
            INSERT INTO bike_station_status (
                station_id, timestamp, bikes_available, docks_available,
                bikes_disabled, docks_disabled, is_installed,
                is_renting, is_returning
            ) VALUES (
                :station_id, :timestamp, :bikes_available, :docks_available,
                :bikes_disabled, :docks_disabled, :is_installed,
                :is_renting, :is_returning
            )
        """)

        session = self.Session()
        try:
            timestamp = datetime.utcnow()
            result = session.execute(
                query,
                [
                    {
                        'station_id': s['station_id'],
                        'timestamp': timestamp,
                        'bikes_available': s['num_bikes_available'],
                        'docks_available': s['num_docks_available'],
                        'bikes_disabled': s.get('num_bikes_disabled', 0),
                        'docks_disabled': s.get('num_docks_disabled', 0),
                        'is_installed': s.get('is_installed', 1) == 1,
                        'is_renting': s.get('is_renting', 1) == 1,
                        'is_returning': s.get('is_returning', 1) == 1
                    }
                    for s in statuses
                ]
            )
            session.commit()
            count = result.rowcount
            logger.info(f"Inserted {count} status records")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert status: {e}")
            raise
        finally:
            session.close()
```

**Key Concepts:**

1. **ON CONFLICT**: Upsert pattern (INSERT or UPDATE if exists)
2. **Batch Insert**: Insert all records in one query (much faster)
3. **Transaction Safety**: Use try/except/finally with rollback
4. **Timestamps**: Use UTC everywhere (avoid timezone issues)

## Backfilling Historical Data

### Step 1: Understanding the Backfill Script

Open `scripts/backfill_historical_data.py`:

```python
#!/usr/bin/env python3
"""
Backfill historical NYC Citi Bike data

This script loads pre-downloaded historical data into the database.
For production, you'd fetch this from Citi Bike's historical data:
https://s3.amazonaws.com/tripdata/index.html
"""

import pandas as pd
from src.data.storage.postgres_handler import PostgreSQLHandler
from loguru import logger
import sys

def load_historical_data():
    """Load historical data from CSV"""
    try:
        # For this tutorial, we use sample data
        # In production, download from:
        # https://s3.amazonaws.com/tripdata/YYYYMM-citibike-tripdata.csv.zip

        logger.info("Loading historical bike data...")

        # Sample: Generate synthetic historical data
        # In production, replace with actual data loading
        from datetime import datetime, timedelta
        import random

        # Generate 30 days of hourly data for 100 stations
        stations = [f"station-{i:03d}" for i in range(1, 101)]
        start_date = datetime.utcnow() - timedelta(days=30)

        data = []
        for station_id in stations:
            for hour in range(30 * 24):  # 30 days * 24 hours
                timestamp = start_date + timedelta(hours=hour)
                data.append({
                    'station_id': station_id,
                    'timestamp': timestamp,
                    'bikes_available': random.randint(0, 25),
                    'docks_available': random.randint(0, 15)
                })

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} historical records")

        return df

    except Exception as e:
        logger.error(f"Failed to load historical data: {e}")
        sys.exit(1)

def main():
    logger.info("Starting historical data backfill...")

    # Load data
    df = load_historical_data()

    # Connect to database
    db = PostgreSQLHandler()

    # Insert in batches (avoid memory issues)
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        records = batch.to_dict('records')

        count = db.insert_station_status(records)
        total_inserted += count

        logger.info(f"Progress: {i+len(batch)}/{len(df)} records")

    logger.info(f"✅ Backfill complete: {total_inserted} records inserted")

if __name__ == "__main__":
    main()
```

### Step 2: Run the Backfill

```bash
# From project root
cd infrastructure

# Start database if not running
docker compose up -d postgres

# Wait for database
sleep 10

# Run backfill
cd ..
docker compose -f infrastructure/docker-compose.yml run --rm \
  -e PYTHONPATH=/app \
  api python scripts/backfill_historical_data.py
```

**Expected Output:**
```
2024-01-01 10:00:00 | INFO | Starting historical data backfill...
2024-01-01 10:00:01 | INFO | Loading historical bike data...
2024-01-01 10:00:02 | INFO | Generated 72000 historical records
2024-01-01 10:00:02 | INFO | Progress: 1000/72000 records
2024-01-01 10:00:03 | INFO | Progress: 2000/72000 records
...
2024-01-01 10:02:00 | INFO | ✅ Backfill complete: 72000 records inserted
```

### Step 3: Verify Data

```bash
# Check data in database
docker compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c "
    SELECT
      COUNT(*) as total_records,
      MIN(timestamp) as earliest,
      MAX(timestamp) as latest,
      COUNT(DISTINCT station_id) as num_stations
    FROM bike_station_status;
  "
```

**Expected:**
```
 total_records |      earliest       |       latest        | num_stations
---------------+---------------------+---------------------+--------------
         72000 | 2024-12-01 10:00:00 | 2024-12-31 09:00:00 |          100
```

## Data Quality Validation

### Why Validate?

Bad data causes:
- ❌ Model training failures
- ❌ Poor predictions
- ❌ Production outages
- ❌ Lost trust in system

**Common Data Issues:**
- Missing values (NULL, NaN)
- Outliers (bikes_available = -5 or 9999)
- Duplicates (same timestamp twice)
- Type mismatches (string instead of number)
- Future timestamps (time travel!)

### Using Great Expectations

Open `src/data/processors/data_validator.py`:

```python
from great_expectations.dataset import PandasDataset
from loguru import logger
from typing import Dict
import pandas as pd

class DataValidator:
    """Validates data quality using Great Expectations"""

    def validate_station_status(self, df: pd.DataFrame) -> Dict:
        """
        Validate bike station status data

        Returns:
            Dict with validation results
        """
        # Convert to Great Expectations dataset
        ge_df = PandasDataset(df)

        results = {}

        # Rule 1: No missing values in critical columns
        results['no_nulls_station_id'] = ge_df.expect_column_values_to_not_be_null(
            'station_id'
        ).success

        results['no_nulls_bikes'] = ge_df.expect_column_values_to_not_be_null(
            'bikes_available'
        ).success

        # Rule 2: Bikes available must be >= 0
        results['bikes_non_negative'] = ge_df.expect_column_values_to_be_between(
            'bikes_available',
            min_value=0,
            max_value=100  # No station has >100 bikes
        ).success

        # Rule 3: Timestamp must be recent (not in future)
        results['timestamp_not_future'] = ge_df.expect_column_values_to_be_between(
            'timestamp',
            min_value=pd.Timestamp('2020-01-01'),  # Reasonable past
            max_value=pd.Timestamp.utcnow()  # Now
        ).success

        # Rule 4: No duplicates
        results['no_duplicates'] = ge_df.expect_compound_columns_to_be_unique(
            ['station_id', 'timestamp']
        ).success

        # Summary
        all_passed = all(results.values())
        logger.info(f"Validation results: {results}")

        if not all_passed:
            logger.warning("⚠️ Some validation rules failed!")

        return results
```

**Test Validation:**
```python
from src.data.processors.data_validator import DataValidator
import pandas as pd
from datetime import datetime, timedelta

# Create test data
good_data = pd.DataFrame([
    {
        'station_id': 'test-001',
        'timestamp': datetime.utcnow(),
        'bikes_available': 10,
        'docks_available': 5
    }
])

bad_data = pd.DataFrame([
    {
        'station_id': None,  # ❌ Missing station_id
        'timestamp': datetime.utcnow() + timedelta(days=10),  # ❌ Future!
        'bikes_available': -5,  # ❌ Negative bikes
        'docks_available': 5
    }
])

validator = DataValidator()

print("Good data:", validator.validate_station_status(good_data))
# {'no_nulls_station_id': True, 'bikes_non_negative': True, ...}

print("Bad data:", validator.validate_station_status(bad_data))
# {'no_nulls_station_id': False, 'bikes_non_negative': False, ...}
```

## Summary

### What You Learned

✅ **API Integration**: Fetching data from REST APIs (Citi Bike, OpenWeatherMap)
✅ **Error Handling**: Timeouts, retries, exception handling
✅ **Database Operations**: Batch inserts, upserts (ON CONFLICT)
✅ **Data Validation**: Great Expectations for quality checks
✅ **Historical Backfilling**: Loading large datasets efficiently

### Data Pipeline Flow

```
APIs → Collectors → Validators → Database → Features → Models
```

### Key Takeaways

1. **Always set timeouts** on HTTP requests (default is infinite)
2. **Batch inserts** are 100x faster than row-by-row
3. **Validate before storing** - garbage in, garbage out
4. **Use ON CONFLICT** for idempotent inserts
5. **Log everything** - you'll need it for debugging

### Data Quality Checks

| Check | Why Important |
|-------|---------------|
| No NULLs in station_id | Can't join data without IDs |
| bikes_available >= 0 | Negative bikes makes no sense |
| timestamp not in future | Can't predict the future |
| No duplicates | Causes issues in aggregations |
| Reasonable ranges | 1000 bikes at one station? Suspicious |

## Next Steps

Now that you have data flowing into the database, head to **[Chapter 4: Feature Engineering Pipeline](04-feature-engineering.md)** to transform raw data into ML features!

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
