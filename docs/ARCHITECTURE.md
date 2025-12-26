# 🏗️ Complete System Architecture Guide

**For Beginners: Build a Production ML System from Scratch**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Technology Stack](#technology-stack)
4. [Database Schema](#database-schema)
5. [Pipeline Details](#pipeline-details)
6. [Docker Containers](#docker-containers)
7. [Data Flow](#data-flow)
8. [Build from Scratch](#build-from-scratch)

---

## System Overview

### What Does This System Do?

This system predicts bike demand at NYC Citi Bike stations using:
- **Real-time bike availability data** from Citi Bike API
- **Weather conditions** from Open-Meteo API
- **Machine Learning models** (XGBoost, LightGBM) trained on historical patterns

### Why is This a "Level 2 MLOps" System?

**MLOps Maturity Levels:**
- **Level 0**: Manual everything (Jupyter notebooks)
- **Level 1**: Some automation (scripts)
- **Level 2**: Automated pipelines + experiment tracking ⭐ **WE ARE HERE**
- **Level 3**: Full CI/CD with monitoring
- **Level 4**: Advanced A/B testing and self-healing

**What makes this Level 2:**
✅ Automated data pipelines (Airflow)
✅ Experiment tracking (MLflow)
✅ Model registry
✅ Containerized deployment (Docker)
✅ Scheduled retraining

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL APIs                             │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │ Citi Bike API    │              │ Open-Meteo API   │         │
│  │ (Station Status) │              │ (Weather Data)   │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
└───────────┼──────────────────────────────────┼──────────────────┘
            │                                  │
            │ Every 15 min                     │ Every 30 min
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AIRFLOW ORCHESTRATION                        │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ Data Ingestion  │  │ Weather         │  │ Feature        │  │
│  │ DAG             │  │ Enrichment DAG  │  │ Engineering    │  │
│  │ (15 min)        │  │ (30 min)        │  │ DAG (1 hour)   │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬───────┘  │
│           │                    │                     │           │
└───────────┼────────────────────┼─────────────────────┼──────────┘
            ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DATABASE                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ bike_station │  │ weather_data │  │ features     │          │
│  │ _status      │  │              │  │              │          │
│  │ (52K rows)   │  │ (1.4K rows)  │  │ (10K rows)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└───────────────────────────────────────┬─────────────────────────┘
                                        │
                                        │ Reads features
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE (Docker)                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ scripts/train_production_model.py                        │   │
│  │                                                          │   │
│  │ 1. Load 10,000 features from database                   │   │
│  │ 2. Split: 70% train / 15% val / 15% test               │   │
│  │ 3. Train XGBoost model                                  │   │
│  │ 4. Train LightGBM model                                 │   │
│  │ 5. Compare models                                       │   │
│  │ 6. Register best model to MLflow                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Logs experiments & models
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MLFLOW TRACKING                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Experiment: bike-demand-production                       │   │
│  │                                                          │   │
│  │ Run 1: XGBoost     → RMSE: 0.63 (Version 2)            │   │
│  │ Run 2: LightGBM    → RMSE: 0.61 (Version 3) ⭐ WINNER  │   │
│  │                                                          │   │
│  │ Model Registry: bike-demand-forecasting v3 → Production │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Serves model
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FASTAPI SERVER                             │
│                                                                  │
│  Endpoints:                                                      │
│  • POST /predict          → Get bike demand prediction           │
│  • GET  /health/detailed  → Check system health                  │
│  • GET  /docs             → API documentation                    │
│                                                                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Displays predictions
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT DASHBOARD                          │
│                                                                  │
│  • Real-time bike demand forecasts                               │
│  • Model performance metrics                                     │
│  • Data quality monitoring                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Infrastructure Layer
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **PostgreSQL** - Relational database (2 instances: app + Airflow)

### Orchestration Layer
- **Apache Airflow** - Workflow scheduling and monitoring
  - Webserver (port 8080)
  - Scheduler (background tasks)
  - Init container (database setup)

### Data Layer
- **Citi Bike API** - Real-time bike station data
- **Open-Meteo API** - Historical weather data (free, no API key)

### ML/AI Layer
- **MLflow** - Experiment tracking & model registry (port 5000)
- **XGBoost** - Gradient boosting model
- **LightGBM** - Fast gradient boosting model
- **scikit-learn** - ML utilities (train/test split, metrics)

### Application Layer
- **FastAPI** - REST API for predictions (port 8000)
- **Streamlit** - Interactive dashboard (port 8501)
- **Pydantic** - Data validation & settings management

### Development Tools
- **pandas** - Data manipulation
- **SQLAlchemy 2.0** - Database ORM
- **loguru** - Beautiful logging
- **pytest** - Testing framework

---

## Database Schema

### Core Tables

#### 1. **bike_stations**
Stores information about each bike station.

```sql
CREATE TABLE bike_stations (
    station_id      VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    latitude        FLOAT NOT NULL,
    longitude       FLOAT NOT NULL,
    capacity        INTEGER,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**Purpose**: Reference table for all bike stations (both active and historical)

**Example Row**:
```
station_id: "66db237e-0aca-11e7-82f6-3863bb44ef7c"
name: "W 52 St & 11 Ave"
latitude: 40.7673
longitude: -73.9939
capacity: 39
is_active: true
```

#### 2. **bike_station_status**
Time-series data of bike availability at each station.

```sql
CREATE TABLE bike_station_status (
    id                  SERIAL PRIMARY KEY,
    station_id          VARCHAR(50) REFERENCES bike_stations(station_id) ON DELETE CASCADE,
    timestamp           TIMESTAMP NOT NULL,
    bikes_available     INTEGER NOT NULL,
    docks_available     INTEGER NOT NULL,
    bikes_disabled      INTEGER DEFAULT 0,
    docks_disabled      INTEGER DEFAULT 0,
    is_installed        BOOLEAN DEFAULT true,
    is_renting          BOOLEAN DEFAULT true,
    is_returning        BOOLEAN DEFAULT true,
    created_at          TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_station_timestamp UNIQUE (station_id, timestamp)
);

CREATE INDEX idx_bike_station_status_station_id ON bike_station_status(station_id);
CREATE INDEX idx_bike_station_status_timestamp ON bike_station_status(timestamp DESC);
CREATE INDEX idx_bike_station_status_station_timestamp ON bike_station_status(station_id, timestamp DESC);
```

**Purpose**: Tracks bike availability over time (collected every 15 minutes)

**Example Row**:
```
station_id: "66db237e-0aca-11e7-82f6-3863bb44ef7c"
timestamp: "2025-11-20 14:00:00"
bikes_available: 12
docks_available: 27
```

#### 3. **weather_data**
Hourly weather conditions for NYC.

```sql
CREATE TABLE weather_data (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMP NOT NULL UNIQUE,
    temperature         FLOAT,
    humidity            FLOAT,
    wind_speed          FLOAT,
    precipitation       FLOAT,
    weather_condition   VARCHAR(50),
    created_at          TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_weather_timestamp UNIQUE (timestamp)
);

CREATE INDEX idx_weather_data_timestamp ON weather_data(timestamp DESC);
```

**Purpose**: Weather context for bike demand predictions

**Example Row**:
```
timestamp: "2025-11-20 14:00:00"
temperature: 15.5  (Celsius)
humidity: 65.0  (%)
wind_speed: 12.3  (km/h)
precipitation: 0.0  (mm)
weather_condition: "Clear"
```

#### 4. **features**
Engineered features combining bike + weather + temporal data.

```sql
CREATE TABLE features (
    id                  SERIAL PRIMARY KEY,
    station_id          VARCHAR(50) REFERENCES bike_stations(station_id) ON DELETE CASCADE,
    timestamp           TIMESTAMP NOT NULL,
    feature_json        JSONB NOT NULL,
    feature_version     VARCHAR(10) NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_station_timestamp_version UNIQUE (station_id, timestamp, feature_version)
);

CREATE INDEX idx_features_station_id ON features(station_id);
CREATE INDEX idx_features_timestamp ON features(timestamp DESC);
CREATE INDEX idx_features_version ON features(feature_version);
```

**Purpose**: Stores 22 engineered features for ML training

**Example feature_json**:
```json
{
  "hour_of_day": 14,
  "day_of_week": 2,
  "day_of_month": 20,
  "month": 11,
  "is_weekend": 0,
  "is_business_hours": 1,
  "is_morning_rush": 0,
  "is_evening_rush": 0,
  "temperature": 15.5,
  "humidity": 65.0,
  "wind_speed": 12.3,
  "precipitation": 0.0,
  "bikes_available": 12,
  "docks_available": 27,
  "bikes_lag_1h": 13,
  "bikes_lag_6h": 15,
  "bikes_lag_24h": 11,
  "docks_lag_1h": 26,
  "docks_lag_6h": 24,
  "docks_lag_24h": 28,
  "bikes_rolling_mean_3h": 13.3,
  "bikes_rolling_std_3h": 1.5,
  "bikes_rolling_mean_6h": 12.8,
  "bikes_rolling_std_6h": 2.1
}
```

#### 5. **predictions** (Optional - for serving)
Stores model predictions for monitoring.

```sql
CREATE TABLE predictions (
    id                          SERIAL PRIMARY KEY,
    station_id                  VARCHAR(50) REFERENCES bike_stations(station_id),
    prediction_timestamp        TIMESTAMP NOT NULL,
    predicted_demand            FLOAT NOT NULL,
    model_version               VARCHAR(20) NOT NULL,
    model_name                  VARCHAR(50) NOT NULL,
    confidence_interval_lower   FLOAT,
    confidence_interval_upper   FLOAT,
    created_at                  TIMESTAMP DEFAULT NOW()
);
```

---

## Pipeline Details

### Pipeline 1: Data Ingestion (Every 15 Minutes)

**File**: `airflow/dags/data_ingestion_dag.py`

**Purpose**: Collect real-time bike station data from Citi Bike API

**Steps**:

```
┌──────────────────────────────────────────────────────┐
│ STEP 1: Start                                        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 2: Collect Station Information                  │
│                                                       │
│ • API: https://gbfs.citibikenyc.com/gbfs/en/         │
│       station_information.json                       │
│ • Extracts:                                          │
│   - station_id, name, lat, lon, capacity             │
│ • Inserts into: bike_stations table                 │
│ • Result: ~2,300 stations                            │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 3: Collect Station Status                       │
│                                                       │
│ • API: https://gbfs.citibikenyc.com/gbfs/en/         │
│       station_status.json                            │
│ • Extracts:                                          │
│   - station_id, bikes_available, docks_available     │
│   - timestamp, is_renting, is_returning              │
│ • Inserts into: bike_station_status table           │
│ • Constraint: Must run AFTER Step 2 (FK dependency) │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 4: Validate Data Quality                        │
│                                                       │
│ • Checks:                                            │
│   - No NULL values in critical columns              │
│   - bikes_available >= 0                            │
│   - docks_available >= 0                            │
│   - Valid timestamp format                          │
│ • If failed: Send alert                             │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 5: Log Metrics                                  │
│                                                       │
│ • Total stations collected                           │
│ • Total status records inserted                      │
│ • Data quality score                                │
│ • Success/Failure                                    │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 6: End                                          │
└──────────────────────────────────────────────────────┘
```

**Key Code** (`src/data/collectors/citi_bike_collector.py`):
```python
def collect_station_information():
    """Collect all bike station information"""
    url = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
    response = requests.get(url)
    data = response.json()

    stations = data['data']['stations']

    for station in stations:
        db.execute(
            "INSERT INTO bike_stations (station_id, name, latitude, longitude, capacity) "
            "VALUES (:id, :name, :lat, :lon, :capacity) "
            "ON CONFLICT (station_id) DO UPDATE SET updated_at = NOW()",
            {
                "id": station['station_id'],
                "name": station['name'],
                "lat": station['lat'],
                "lon": station['lon'],
                "capacity": station['capacity']
            }
        )
```

**Critical Constraint**:
```python
# DAG task dependencies - MUST be sequential!
start >> task_collect_station_info >> task_collect_station_status
# WHY? bike_station_status has FK to bike_stations
```

---

### Pipeline 2: Weather Enrichment (Every 30 Minutes)

**File**: `airflow/dags/weather_enrichment_dag.py`

**Purpose**: Fetch hourly weather data for NYC

**Steps**:

```
┌──────────────────────────────────────────────────────┐
│ STEP 1: Start                                        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 2: Fetch Weather Data                           │
│                                                       │
│ • API: OpenWeatherMap API                            │
│ • Location: NYC (lat: 40.7128, lon: -74.0060)       │
│ • Extracts:                                          │
│   - temperature, humidity, wind_speed                │
│   - precipitation, weather_condition                 │
│ • Inserts into: weather_data table                  │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 3: Validate Weather Data                        │
│                                                       │
│ • Temperature range check (-20°C to 45°C)           │
│ • Humidity range check (0% to 100%)                 │
│ • Wind speed >= 0                                   │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 4: Log Metrics                                  │
└──────────────────────────────────────────────────────┘
```

**Key Code** (`src/data/collectors/weather_collector.py`):
```python
def collect_weather():
    """Collect current weather for NYC"""
    api_key = os.getenv('WEATHER_API_KEY')
    url = f"https://api.openweathermap.org/data/2.5/weather?lat=40.7128&lon=-74.0060&appid={api_key}&units=metric"

    response = requests.get(url)
    data = response.json()

    db.execute(
        "INSERT INTO weather_data (timestamp, temperature, humidity, wind_speed, precipitation, weather_condition) "
        "VALUES (NOW(), :temp, :humidity, :wind, :precip, :condition) "
        "ON CONFLICT (timestamp) DO UPDATE SET temperature = EXCLUDED.temperature",
        {
            "temp": data['main']['temp'],
            "humidity": data['main']['humidity'],
            "wind": data['wind']['speed'],
            "precip": data.get('rain', {}).get('1h', 0),
            "condition": data['weather'][0]['main']
        }
    )
```

---

### Pipeline 3: Feature Engineering (Every 1 Hour)

**File**: `airflow/dags/feature_engineering_dag.py`

**Purpose**: Combine bike status + weather + create ML features

**Steps**:

```
┌──────────────────────────────────────────────────────┐
│ STEP 1: Load Raw Data                                │
│                                                       │
│ • Query last 7 days of bike_station_status          │
│ • Query last 7 days of weather_data                 │
│ • Merge on timestamp (hourly)                       │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 2: Generate Temporal Features                   │
│                                                       │
│ • hour_of_day: 0-23                                  │
│ • day_of_week: 0-6 (Monday=0)                       │
│ • day_of_month: 1-31                                │
│ • month: 1-12                                       │
│ • is_weekend: 1 if Sat/Sun, else 0                  │
│ • is_business_hours: 1 if 9am-5pm, else 0          │
│ • is_morning_rush: 1 if 7am-9am, else 0            │
│ • is_evening_rush: 1 if 5pm-7pm, else 0            │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 3: Generate Lag Features                        │
│                                                       │
│ • bikes_lag_1h: bikes 1 hour ago                    │
│ • bikes_lag_6h: bikes 6 hours ago                   │
│ • bikes_lag_24h: bikes 24 hours ago                 │
│ • docks_lag_1h: docks 1 hour ago                    │
│ • docks_lag_6h: docks 6 hours ago                   │
│ • docks_lag_24h: docks 24 hours ago                 │
│                                                       │
│ Implementation:                                      │
│   df['bikes_lag_1h'] = df.groupby('station_id')     │
│                         ['bikes_available']          │
│                         .shift(1)                    │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 4: Generate Rolling Features                    │
│                                                       │
│ • bikes_rolling_mean_3h: Avg bikes in last 3h       │
│ • bikes_rolling_std_3h: Std dev bikes in last 3h    │
│ • bikes_rolling_mean_6h: Avg bikes in last 6h       │
│ • bikes_rolling_std_6h: Std dev bikes in last 6h    │
│                                                       │
│ Implementation:                                      │
│   df['bikes_rolling_mean_3h'] =                     │
│       df.groupby('station_id')['bikes_available']   │
│         .rolling(window=3, min_periods=1)           │
│         .mean()                                     │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 5: Add Weather Features                         │
│                                                       │
│ • temperature (from weather_data)                    │
│ • humidity (from weather_data)                       │
│ • wind_speed (from weather_data)                     │
│ • precipitation (from weather_data)                  │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 6: Save to features Table                       │
│                                                       │
│ • Store as JSONB in feature_json column             │
│ • Tag with feature_version = "v1"                   │
│ • Create unique constraint on                       │
│   (station_id, timestamp, feature_version)          │
└──────────────────────────────────────────────────────┘
```

**Key Code** (`scripts/generate_features.py`):
```python
# Merge bike status with weather
merged = status_df.merge(
    weather_df[['hour', 'temperature', 'humidity', 'wind_speed', 'precipitation']],
    on='hour',
    how='left'
)

# Temporal features
merged['hour_of_day'] = merged['timestamp'].dt.hour
merged['day_of_week'] = merged['timestamp'].dt.dayofweek
merged['is_weekend'] = (merged['day_of_week'] >= 5).astype(int)

# Lag features
for lag_hours in [1, 6, 24]:
    merged[f'bikes_lag_{lag_hours}h'] = merged.groupby('station_id')['bikes_available'].shift(lag_hours)

# Rolling features
for window_hours in [3, 6]:
    merged[f'bikes_rolling_mean_{window_hours}h'] = merged.groupby('station_id')['bikes_available'] \
        .transform(lambda x: x.rolling(window=window_hours, min_periods=1).mean())
```

---

### Pipeline 4: Model Training (Daily at 2 AM)

**File**: `docker/training/Dockerfile` + `scripts/train_production_model.py`

**Purpose**: Train ML models and register best model to production

**Steps**:

```
┌──────────────────────────────────────────────────────┐
│ STEP 1: Load Features from Database                  │
│                                                       │
│ • Query: SELECT * FROM features                      │
│          WHERE feature_version = 'v1'                │
│          ORDER BY timestamp                          │
│ • Result: 10,000 records with 22 features           │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 2: Parse JSON Features                          │
│                                                       │
│ • feature_json (JSONB) → pandas DataFrame           │
│ • Columns: [hour_of_day, day_of_week, temperature,  │
│            humidity, bikes_lag_1h, ..., etc]        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 3: Prepare X and y                              │
│                                                       │
│ • Target (y): bikes_available                        │
│ • Features (X): All 22 features except target       │
│ • Remove: station_id, timestamp, docks_available    │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 4: Train/Val/Test Split (Time-Series!)         │
│                                                       │
│ • NO SHUFFLING (time-series data)                   │
│ • Train: 70% oldest (7,004 records)                 │
│ • Val:   15% middle  (1,496 records)                │
│ • Test:  15% newest  (1,500 records)                │
│                                                       │
│ Why no shuffle?                                     │
│   → Future cannot predict past                      │
│   → Prevents data leakage                           │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 5: Train XGBoost Model                          │
│                                                       │
│ • Hyperparameters:                                   │
│   - n_estimators: 200                               │
│   - max_depth: 8                                    │
│   - learning_rate: 0.05                             │
│   - subsample: 0.8                                  │
│   - colsample_bytree: 0.8                           │
│                                                       │
│ • Training: model.fit(X_train, y_train)             │
│                                                       │
│ • Evaluation:                                        │
│   - Val RMSE: 0.77                                  │
│   - Test RMSE: 0.63                                 │
│   - Test R²: 0.6090                                 │
│                                                       │
│ • Log to MLflow:                                     │
│   - Parameters                                       │
│   - Metrics                                          │
│   - Model artifact                                   │
│   - Register as version 2                           │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 6: Train LightGBM Model                         │
│                                                       │
│ • Same hyperparameters as XGBoost                   │
│                                                       │
│ • Evaluation:                                        │
│   - Val RMSE: 0.77                                  │
│   - Test RMSE: 0.61 ⭐ BETTER!                      │
│   - Test R²: 0.6309                                 │
│                                                       │
│ • Register as version 3                             │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 7: Model Comparison                             │
│                                                       │
│ • XGBoost:  RMSE = 0.63                             │
│ • LightGBM: RMSE = 0.61 ✅ WINNER                   │
│                                                       │
│ • Decision: Promote LightGBM v3 to Production       │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│ STEP 8: Promote Best Model to Production             │
│                                                       │
│ • MLflow Registry Action:                            │
│   client.transition_model_version_stage(            │
│       name="bike-demand-forecasting",               │
│       version=3,                                     │
│       stage="Production",                            │
│       archive_existing_versions=True                │
│   )                                                  │
│                                                       │
│ • Previous Production models → Archived             │
│ • New Production model: LightGBM v3                 │
└──────────────────────────────────────────────────────┘
```

**Key Code** (`scripts/train_production_model.py`):
```python
# XGBoost training
with mlflow.start_run(run_name="xgboost_production"):
    params = {'n_estimators': 200, 'max_depth': 8, 'learning_rate': 0.05}
    mlflow.log_params(params)

    model = XGBRegressor(**params)
    model.fit(X_train, y_train)

    test_pred = model.predict(X_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))

    mlflow.log_metric('test_rmse', test_rmse)
    mlflow.sklearn.log_model(model, "model", registered_model_name="bike-demand-forecasting")

# Promote best model
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="bike-demand-forecasting",
    version=latest_version,
    stage="Production"
)
```

---

## Docker Containers

### Container 1: PostgreSQL (Main Database)

**Service Name**: `postgres`
**Port**: 5432
**Database**: `bike_demand_db`

**Purpose**: Stores all application data (bike status, weather, features)

**docker-compose.yml**:
```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: bike_demand_db
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Container 2: MLflow

**Service Name**: `mlflow`
**Port**: 5000
**Storage**: Docker volume `mlflow_data`

**Purpose**: Experiment tracking & model registry

**docker-compose.yml**:
```yaml
mlflow:
  image: ghcr.io/mlflow/mlflow:latest
  command: >
    mlflow server
    --backend-store-uri file:///mlflow/backend
    --default-artifact-root file:///mlflow/artifacts
    --host 0.0.0.0
    --port 5000
    --serve-artifacts
  ports:
    - "5000:5000"
  volumes:
    - mlflow_data:/mlflow
```

**Access**: http://localhost:5000

### Container 3: Airflow PostgreSQL

**Service Name**: `airflow-postgres`
**Port**: 5433
**Database**: `airflow_db`

**Purpose**: Airflow metadata database (separate from app data)

### Container 4: Airflow Webserver

**Service Name**: `airflow-webserver`
**Port**: 8080
**Username**: `airflow`
**Password**: `airflow`

**Purpose**: Airflow UI for monitoring DAGs

**Key Environment Variables**:
```yaml
environment:
  DB_HOST: postgres
  DB_PORT: 5432
  DB_USER: postgres
  DB_PASSWORD: postgres
  DB_DATABASE: bike_demand_db
  MLFLOW_TRACKING_URI: http://mlflow:5000
  PYTHONPATH: '/opt/airflow:/opt/airflow/src'
```

**Why these variables?**
→ Allows Airflow DAGs to connect to PostgreSQL and MLflow

### Container 5: Airflow Scheduler

**Service Name**: `airflow-scheduler`
**Purpose**: Executes DAGs on schedule

**Same environment variables as webserver**

### Container 6: Training Container (On-Demand)

**Image**: `bike-demand-trainer:latest`
**Dockerfile**: `docker/training/Dockerfile`

**Purpose**: Trains ML models in isolated environment

**Build**:
```bash
docker build -f docker/training/Dockerfile -t bike-demand-trainer:latest .
```

**Run**:
```bash
docker run --rm \
  --network host \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  bike-demand-trainer:latest
```

**What it does**:
1. Loads features from PostgreSQL
2. Trains XGBoost + LightGBM
3. Logs experiments to MLflow
4. Promotes best model to Production

---

## Data Flow

### End-to-End Flow (15-Minute Cycle)

```
TIME: 00:00
┌─────────────────────────────────────────────────────────────┐
│ Citi Bike API                                                │
│ https://gbfs.citibikenyc.com/gbfs/en/station_status.json    │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ HTTP GET
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Airflow DAG: data_ingestion (triggered every 15 min)        │
│ Task: collect_station_status()                               │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ INSERT INTO bike_station_status
               ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL: bike_station_status                              │
│ New row: station_id='abc123', timestamp='00:00',            │
│          bikes_available=12, docks_available=27             │
└─────────────────────────────────────────────────────────────┘

TIME: 00:30
┌─────────────────────────────────────────────────────────────┐
│ Open-Meteo API                                               │
│ https://archive-api.open-meteo.com/v1/archive              │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ HTTP GET
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Airflow DAG: weather_enrichment (triggered every 30 min)    │
│ Task: fetch_weather()                                        │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ INSERT INTO weather_data
               ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL: weather_data                                     │
│ New row: timestamp='00:00', temperature=15.5,               │
│          humidity=65, wind_speed=12.3                       │
└─────────────────────────────────────────────────────────────┘

TIME: 01:00
┌─────────────────────────────────────────────────────────────┐
│ Airflow DAG: feature_engineering (triggered every 1 hour)   │
│ Task: generate_features()                                    │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ SELECT FROM bike_station_status + weather_data
               │ JOIN + CREATE lag/rolling features
               ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL: features                                         │
│ New row: station_id='abc123', timestamp='00:00',            │
│          feature_json={22 features...}                      │
└─────────────────────────────────────────────────────────────┘

TIME: 02:00 (Daily)
┌─────────────────────────────────────────────────────────────┐
│ Docker Container: bike-demand-trainer                        │
│ Command: python scripts/train_production_model.py           │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ SELECT FROM features
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Training: XGBoost + LightGBM                                 │
│ Evaluation: Compare RMSE                                     │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ Log experiments + models
               ▼
┌─────────────────────────────────────────────────────────────┐
│ MLflow: bike-demand-forecasting v3 → Production              │
└─────────────────────────────────────────────────────────────┘
```

---

## Build from Scratch

### Prerequisites

```bash
# Required software
- Docker Desktop
- Python 3.11+
- Git

# Check installations
docker --version       # Should be 20.10+
python --version       # Should be 3.11+
```

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd Bike-Demand-Prediction-for-Smart-Cities
```

### Step 2: Set Up Environment

```bash
# Create .env file
cat > .env << EOF
WEATHER_API_KEY=f57895b988e11368c6b38a3cb983b6ec
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bike_demand_db
MLFLOW_TRACKING_URI=http://localhost:5000
EOF
```

### Step 3: Start Infrastructure

```bash
# Start PostgreSQL and MLflow
docker-compose -f infrastructure/docker-compose.yml up -d postgres mlflow

# Wait 30 seconds for services to be healthy
sleep 30

# Verify
docker-compose -f infrastructure/docker-compose.yml ps
```

**Expected**:
```
NAME                   STATUS              PORTS
bike_demand_mlflow     running (healthy)   0.0.0.0:5000->5000/tcp
bike_demand_postgres   running (healthy)   0.0.0.0:5432->5432/tcp
```

### Step 4: Initialize Airflow

```bash
# First time only - initialize Airflow database
docker-compose -f infrastructure/docker-compose.yml up -d airflow-init

# Wait 45 seconds
sleep 45

# Start Airflow services
docker-compose -f infrastructure/docker-compose.yml up -d airflow-webserver airflow-scheduler

# Verify
docker-compose -f infrastructure/docker-compose.yml ps airflow-scheduler airflow-webserver
```

**Access Airflow UI**: http://localhost:8080
**Login**: airflow / airflow

### Step 5: Trigger Data Collection

```bash
# Trigger data ingestion DAG (collects bike station data)
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger citi_bike_data_ingestion

# Wait 2 minutes

# Trigger weather enrichment DAG
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger weather_enrichment

# Wait 1 minute
```

### Step 6: Verify Data Collection

```bash
docker-compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c \
  "SELECT COUNT(*) as stations FROM bike_stations;
   SELECT COUNT(*) as statuses FROM bike_station_status;
   SELECT COUNT(*) as weather FROM weather_data;"
```

**Expected**:
```
stations: ~2300
statuses: ~2300
weather: 1+
```

### Step 7: Backfill Historical Data

```bash
# Install Python dependencies (if running scripts on host)
pip install pandas numpy requests loguru sqlalchemy psycopg2-binary

# Backfill bike station data (Nov 2025 - 50K records)
python scripts/backfill_historical_data.py

# Backfill weather data
python scripts/backfill_weather.py
```

### Step 8: Generate Features

```bash
python scripts/generate_features.py
```

**Result**: 10,000 features in database

### Step 9: Train Model (Docker)

```bash
# Build training image
docker build -f docker/training/Dockerfile -t bike-demand-trainer:latest .

# Run training
docker run --rm \
  --network host \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  bike-demand-trainer:latest
```

**Result**: LightGBM model v3 promoted to Production

### Step 10: Start API Server

```bash
# Install API dependencies
pip install fastapi uvicorn

# Start FastAPI server
uvicorn src.serving.api.main:app --host 0.0.0.0 --port 8000 &

# Test health endpoint
curl http://localhost:8000/health/detailed | python -m json.tool
```

### Step 11: Start Dashboard

```bash
# Install dashboard dependencies
pip install streamlit

# Start Streamlit dashboard
streamlit run dashboard/app.py --server.port 8501 &
```

**Access Dashboard**: http://localhost:8501

---

## System Health Check

```bash
# Check all Docker containers
docker-compose -f infrastructure/docker-compose.yml ps

# Check database
docker-compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c \
  "SELECT
    (SELECT COUNT(*) FROM bike_stations) as stations,
    (SELECT COUNT(*) FROM bike_station_status) as statuses,
    (SELECT COUNT(*) FROM weather_data) as weather,
    (SELECT COUNT(*) FROM features) as features;"

# Check MLflow model
curl -s "http://localhost:5000/api/2.0/mlflow/registered-models/get?name=bike-demand-forecasting" \
  | python -m json.tool | grep -E "(version|current_stage)"

# Check Airflow DAGs
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags list | grep -E "(citi_bike|weather|feature|model)"

# Check API health
curl http://localhost:8000/health/detailed | python -m json.tool
```

---

## Troubleshooting

### Issue 1: Airflow Can't Connect to PostgreSQL

**Symptom**: `psycopg2.OperationalError: connection refused`

**Fix**: Ensure environment variables are set in `docker-compose.yml`:
```yaml
airflow-scheduler:
  environment:
    DB_HOST: postgres  # NOT localhost!
    DB_PORT: 5432
    DB_USER: postgres
    DB_PASSWORD: postgres
    DB_DATABASE: bike_demand_db
```

### Issue 2: Foreign Key Constraint Violation

**Symptom**: `ForeignKeyViolation: bike_station_status violates FK constraint`

**Fix**: Ensure DAG tasks run sequentially:
```python
# CORRECT
start >> task_collect_station_info >> task_collect_station_status

# WRONG (parallel will fail)
start >> [task_collect_station_info, task_collect_station_status]
```

### Issue 3: Model Artifacts Not Found

**Symptom**: `OSError: No such file or directory: '/mlflow/artifacts/...'`

**Fix**: Use `--network host` when running training container:
```bash
docker run --rm --network host -e MLFLOW_TRACKING_URI=http://localhost:5000 bike-demand-trainer:latest
```

---

## Key Learnings

### 1. Time-Series Data Best Practices

**❌ DON'T**:
```python
# BAD: Shuffling time-series data causes data leakage
X_train, X_test = train_test_split(X, y, shuffle=True)  # WRONG!
```

**✅ DO**:
```python
# GOOD: Preserve time order
X_train, X_test = train_test_split(X, y, shuffle=False)  # Correct!
# Train on past, validate on middle, test on future
```

### 2. Docker Networking

**Inside Docker containers**:
```python
# Use service names, NOT localhost
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/bike_demand_db"
                                              ^^^^^^^^
MLFLOW_TRACKING_URI = "http://mlflow:5000"
                             ^^^^^^^
```

**From host machine**:
```python
# Use localhost
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/bike_demand_db"
                                              ^^^^^^^^^
MLFLOW_TRACKING_URI = "http://localhost:5000"
                             ^^^^^^^^^
```

### 3. Feature Engineering for Time-Series

**Critical features**:
- **Lag features**: Past values (1h, 6h, 24h ago)
- **Rolling statistics**: Moving averages, std dev
- **Temporal features**: Hour, day of week, is_weekend
- **Contextual features**: Weather, holidays

**Why?**
→ ML models can't see the past unless you explicitly provide it!

---

## Next Steps

### Production Enhancements

1. **Add Monitoring**
   - Evidently AI for data drift detection
   - Prometheus + Grafana for system metrics

2. **Add CI/CD**
   - GitHub Actions for automated testing
   - Automated model deployment

3. **Add Model Serving at Scale**
   - Deploy API in Docker
   - Add model versioning endpoint
   - Implement batch prediction

4. **Add Data Versioning**
   - DVC for dataset versioning
   - Track data lineage

---

## Summary

This is a **production-grade Level 2 MLOps system** that:

✅ Automates data collection (Airflow)
✅ Tracks experiments (MLflow)
✅ Registers models (MLflow Registry)
✅ Trains in Docker (reproducible)
✅ Serves predictions (FastAPI)
✅ Visualizes results (Streamlit)

**Total Components**: 6 Docker containers, 4 Airflow DAGs, 4 database tables, 2 ML models

**Production Ready**: Yes! This system can run 24/7 with minimal human intervention.

---

**For Support**: See [PRODUCTION_SETUP_COMPLETE.md](PRODUCTION_SETUP_COMPLETE.md)
**For Troubleshooting**: See "Troubleshooting" section above
