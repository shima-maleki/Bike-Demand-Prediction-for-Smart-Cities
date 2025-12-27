# Chapter 8: Orchestration with Airflow

## Overview

This chapter guides you through automating your entire ML pipeline using Apache Airflow - from data ingestion every 15 minutes to daily model retraining.

**What You'll Build**:
- Data ingestion DAG (runs every 15 minutes)
- Weather enrichment DAG (runs every 30 minutes)
- Feature engineering DAG (runs hourly)
- Model training DAG (runs daily at 2 AM)

**Estimated Time**: 3-4 hours

## Why Apache Airflow?

**Decision**: Airflow vs. Cron vs. Kubernetes CronJobs vs. Prefect

**Why Airflow Won**:
- **Visual Workflow**: DAG graph view shows pipeline dependencies
- **Retry Logic**: Automatic retries on failure with exponential backoff
- **Monitoring**: Built-in logging, alerting, and execution history
- **Scalability**: CeleryExecutor for distributed task execution
- **Python-Native**: Write workflows in Python, not YAML

**Comparison**:

| Feature | Airflow | Cron | K8s CronJobs | Prefect |
|---------|---------|------|--------------|---------|
| **Visual UI** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Dependencies** | ✅ DAG | ❌ Manual | ❌ Manual | ✅ Flow |
| **Retry Logic** | ✅ Built-in | ❌ Manual | ✅ Yes | ✅ Yes |
| **Monitoring** | ✅ Rich | ❌ Basic | ⚠️ Limited | ✅ Rich |
| **Complexity** | ⚠️ Medium | ✅ Simple | ⚠️ High | ⚠️ Medium |
| **Cost** | ✅ Free | ✅ Free | ⚠️ K8s cost | 💰 Paid tiers |

**Result**: Airflow provides the best balance of power, visibility, and cost for our use case.

---

## Architecture

```
Airflow Scheduler
    ↓
┌─────────────────────────────────────────────┐
│  DAG 1: Data Ingestion (every 15 min)      │
│  ├─ Fetch station status from Citi Bike API│
│  ├─ Validate data quality                   │
│  └─ Insert into PostgreSQL                  │
└─────────────────────────────────────────────┘
    ↓ (triggers)
┌─────────────────────────────────────────────┐
│  DAG 2: Weather Enrichment (every 30 min)  │
│  ├─ Fetch weather from OpenWeatherMap      │
│  ├─ Join with station data                  │
│  └─ Store in weather_data table            │
└─────────────────────────────────────────────┘
    ↓ (triggers)
┌─────────────────────────────────────────────┐
│  DAG 3: Feature Engineering (hourly)       │
│  ├─ Generate temporal features              │
│  ├─ Calculate lag features                  │
│  ├─ Compute rolling features                │
│  └─ Store in features table (JSONB)        │
└─────────────────────────────────────────────┘
    ↓ (triggers)
┌─────────────────────────────────────────────┐
│  DAG 4: Model Training (daily 2 AM)        │
│  ├─ Load features from PostgreSQL           │
│  ├─ Train XGBoost + LightGBM                │
│  ├─ Evaluate on validation set              │
│  ├─ Log metrics to MLflow                   │
│  └─ Promote best model to Production        │
└─────────────────────────────────────────────┘
```

**Data Flow**: API → PostgreSQL → Features → Model → Predictions

---

## Step 1: Airflow Setup

### `docker/airflow/Dockerfile`

```dockerfile
FROM apache/airflow:2.8.0-python3.11

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    apache-airflow-providers-postgres==5.10.0 \
    psycopg2-binary==2.9.9 \
    pandas==2.1.4 \
    requests==2.31.0 \
    sqlalchemy==2.0.25 \
    great-expectations==0.18.8 \
    mlflow==2.9.2 \
    xgboost==2.0.3 \
    lightgbm==4.1.0 \
    scikit-learn==1.3.2

# Copy DAGs
COPY airflow/dags/ ${AIRFLOW_HOME}/dags/

# Copy source code
COPY src/ ${AIRFLOW_HOME}/src/
```

### `infrastructure/docker-compose.yml` (Airflow services)

```yaml
services:
  # ... existing services (postgres, mlflow, api) ...

  airflow-init:
    image: bike-demand-airflow:latest
    build:
      context: ..
      dockerfile: docker/airflow/Dockerfile
    environment:
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@postgres:5432/airflow_db
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - _AIRFLOW_DB_MIGRATE=true
      - _AIRFLOW_WWW_USER_CREATE=true
      - _AIRFLOW_WWW_USER_USERNAME=admin
      - _AIRFLOW_WWW_USER_PASSWORD=admin
    depends_on:
      - postgres
    networks:
      - bike-demand-network
    command: version

  airflow-webserver:
    image: bike-demand-airflow:latest
    build:
      context: ..
      dockerfile: docker/airflow/Dockerfile
    ports:
      - "8080:8080"
    environment:
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@postgres:5432/airflow_db
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__WEBSERVER__SECRET_KEY=your-secret-key-here
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=bike_demand_db
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    depends_on:
      - airflow-init
    networks:
      - bike-demand-network
    volumes:
      - airflow-logs:/opt/airflow/logs
    command: webserver

  airflow-scheduler:
    image: bike-demand-airflow:latest
    build:
      context: ..
      dockerfile: docker/airflow/Dockerfile
    environment:
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@postgres:5432/airflow_db
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=bike_demand_db
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    depends_on:
      - airflow-init
    networks:
      - bike-demand-network
    volumes:
      - airflow-logs:/opt/airflow/logs
    command: scheduler

volumes:
  airflow-logs:

networks:
  bike-demand-network:
    driver: bridge
```

**Key Configuration**:
- **Executor**: `LocalExecutor` (uses PostgreSQL for task queue)
- **Database**: Separate `airflow_db` for Airflow metadata
- **No Examples**: `LOAD_EXAMPLES=False` to keep UI clean
- **Shared Network**: All services communicate via `bike-demand-network`

---

## Step 2: Data Ingestion DAG

### `airflow/dags/data_ingestion_dag.py`

```python
"""
DAG: Data Ingestion
Schedule: Every 15 minutes
Purpose: Fetch bike station status from Citi Bike API and store in PostgreSQL
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import requests
import logging
from typing import List, Dict

# Default arguments for all tasks
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30)
}

# DAG definition
dag = DAG(
    'data_ingestion',
    default_args=default_args,
    description='Fetch bike station data every 15 minutes',
    schedule_interval='*/15 * * * *',  # Cron: every 15 minutes
    catchup=False,  # Don't backfill historical runs
    max_active_runs=1,  # Only one run at a time
    tags=['data-collection', 'real-time']
)

# --- Task Functions ---

def fetch_station_information(**context) -> List[Dict]:
    """
    Fetch static station information (station_id, name, lat, lon, capacity)
    This data changes rarely, so we only update it if new stations appear.
    """
    logging.info("Fetching station information from Citi Bike API...")

    url = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    stations = data['data']['stations']

    logging.info(f"Fetched {len(stations)} stations")

    # Push to XCom for next task
    context['ti'].xcom_push(key='stations', value=stations)

    return stations

def fetch_station_status(**context) -> List[Dict]:
    """
    Fetch real-time station status (bikes_available, docks_available)
    This changes every few minutes.
    """
    logging.info("Fetching station status from Citi Bike API...")

    url = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    statuses = data['data']['stations']

    logging.info(f"Fetched status for {len(statuses)} stations")

    # Add timestamp
    fetch_time = datetime.now()
    for status in statuses:
        status['fetch_timestamp'] = fetch_time.isoformat()

    context['ti'].xcom_push(key='statuses', value=statuses)

    return statuses

def validate_data(**context):
    """
    Validate data quality using basic checks
    (Great Expectations integration can be added here)
    """
    statuses = context['ti'].xcom_pull(key='statuses', task_ids='fetch_station_status')

    if not statuses:
        raise ValueError("No station status data to validate")

    # Basic validation
    errors = []

    for status in statuses:
        # Check required fields
        if 'station_id' not in status:
            errors.append(f"Missing station_id in record: {status}")

        if 'num_bikes_available' not in status:
            errors.append(f"Missing bikes count for station {status.get('station_id')}")

        # Check data ranges
        bikes = status.get('num_bikes_available', 0)
        docks = status.get('num_docks_available', 0)

        if bikes < 0 or docks < 0:
            errors.append(f"Negative counts for station {status.get('station_id')}: bikes={bikes}, docks={docks}")

    if errors:
        logging.warning(f"Data validation found {len(errors)} issues")
        for error in errors[:10]:  # Log first 10
            logging.warning(error)

        # Decide: fail task or continue with valid records
        if len(errors) > len(statuses) * 0.5:  # More than 50% invalid
            raise ValueError(f"Too many validation errors: {len(errors)}/{len(statuses)}")

    logging.info(f"Validation passed: {len(statuses)} records validated")

def upsert_station_information(**context):
    """
    Upsert station information into bike_stations table
    Uses ON CONFLICT to update if station already exists
    """
    stations = context['ti'].xcom_pull(key='stations', task_ids='fetch_station_information')

    if not stations:
        logging.warning("No stations to insert")
        return

    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()

    upsert_query = """
    INSERT INTO bike_stations (station_id, name, latitude, longitude, capacity, is_active)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (station_id)
    DO UPDATE SET
        name = EXCLUDED.name,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        capacity = EXCLUDED.capacity,
        is_active = EXCLUDED.is_active,
        updated_at = CURRENT_TIMESTAMP
    """

    records = [
        (
            station['station_id'],
            station.get('name', 'Unknown'),
            station.get('lat', 0.0),
            station.get('lon', 0.0),
            station.get('capacity', 0),
            not station.get('is_renting_disabled', False)  # is_active
        )
        for station in stations
    ]

    cursor.executemany(upsert_query, records)
    conn.commit()

    logging.info(f"Upserted {len(records)} station records")

    cursor.close()
    conn.close()

def insert_station_status(**context):
    """
    Insert station status into bike_station_status table
    This is time-series data, so we always INSERT (never update)
    """
    statuses = context['ti'].xcom_pull(key='statuses', task_ids='fetch_station_status')

    if not statuses:
        logging.warning("No statuses to insert")
        return

    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO bike_station_status (station_id, timestamp, bikes_available, docks_available)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (station_id, timestamp) DO NOTHING
    """

    records = [
        (
            status['station_id'],
            datetime.fromisoformat(status['fetch_timestamp']),
            status.get('num_bikes_available', 0),
            status.get('num_docks_available', 0)
        )
        for status in statuses
    ]

    cursor.executemany(insert_query, records)
    inserted_count = cursor.rowcount
    conn.commit()

    logging.info(f"Inserted {inserted_count} station status records")

    cursor.close()
    conn.close()

# --- Define Tasks ---

task_fetch_stations = PythonOperator(
    task_id='fetch_station_information',
    python_callable=fetch_station_information,
    dag=dag
)

task_fetch_status = PythonOperator(
    task_id='fetch_station_status',
    python_callable=fetch_station_status,
    dag=dag
)

task_validate = PythonOperator(
    task_id='validate_data',
    python_callable=validate_data,
    dag=dag
)

task_upsert_stations = PythonOperator(
    task_id='upsert_station_information',
    python_callable=upsert_station_information,
    dag=dag
)

task_insert_status = PythonOperator(
    task_id='insert_station_status',
    python_callable=insert_station_status,
    dag=dag
)

# --- Task Dependencies ---

# Parallel fetch
[task_fetch_stations, task_fetch_status]

# Validate after fetch
task_fetch_status >> task_validate

# Insert after validation
task_validate >> task_insert_status
task_fetch_stations >> task_upsert_stations
```

**Key Concepts**:

1. **Schedule**: `*/15 * * * *` = every 15 minutes
2. **Retry Logic**: 3 retries with exponential backoff (5 min → 10 min → 20 min)
3. **XCom**: Share data between tasks using `xcom_push` and `xcom_pull`
4. **Idempotency**: `ON CONFLICT DO NOTHING` prevents duplicate inserts
5. **Catchup**: `False` means don't backfill historical runs
6. **Max Active Runs**: `1` prevents overlapping executions

---

## Step 3: Weather Enrichment DAG

### `airflow/dags/weather_enrichment_dag.py`

```python
"""
DAG: Weather Enrichment
Schedule: Every 30 minutes
Purpose: Fetch weather data for NYC and join with station data
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import requests
import logging
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'weather_enrichment',
    default_args=default_args,
    description='Fetch weather data every 30 minutes',
    schedule_interval='*/30 * * * *',  # Every 30 minutes
    catchup=False,
    tags=['data-collection', 'weather']
)

def fetch_weather_data(**context):
    """
    Fetch current weather for NYC from OpenWeatherMap API
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')

    if not api_key:
        logging.warning("OPENWEATHER_API_KEY not set. Using mock data.")
        # Mock data for development
        weather_data = {
            'temperature': 15.5,
            'humidity': 65,
            'wind_speed': 5.2,
            'precipitation': 0.0,
            'weather_condition': 'Clear',
            'timestamp': datetime.now().isoformat()
        }
    else:
        # NYC coordinates
        lat, lon = 40.7128, -74.0060

        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        weather_data = {
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed'],
            'precipitation': data.get('rain', {}).get('1h', 0.0),  # Rain in last 1 hour
            'weather_condition': data['weather'][0]['main'],
            'timestamp': datetime.now().isoformat()
        }

    logging.info(f"Fetched weather: {weather_data['temperature']}°C, {weather_data['weather_condition']}")

    context['ti'].xcom_push(key='weather_data', value=weather_data)

    return weather_data

def insert_weather_data(**context):
    """
    Insert weather data into weather_data table
    """
    weather = context['ti'].xcom_pull(key='weather_data', task_ids='fetch_weather')

    if not weather:
        raise ValueError("No weather data to insert")

    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO weather_data (timestamp, temperature, humidity, wind_speed, precipitation, weather_condition)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (timestamp) DO NOTHING
    """

    cursor.execute(insert_query, (
        datetime.fromisoformat(weather['timestamp']),
        weather['temperature'],
        weather['humidity'],
        weather['wind_speed'],
        weather['precipitation'],
        weather['weather_condition']
    ))

    conn.commit()
    logging.info("Weather data inserted successfully")

    cursor.close()
    conn.close()

# Tasks
task_fetch_weather = PythonOperator(
    task_id='fetch_weather',
    python_callable=fetch_weather_data,
    dag=dag
)

task_insert_weather = PythonOperator(
    task_id='insert_weather',
    python_callable=insert_weather_data,
    dag=dag
)

# Dependencies
task_fetch_weather >> task_insert_weather
```

---

## Step 4: Feature Engineering DAG

### `airflow/dags/feature_engineering_dag.py`

```python
"""
DAG: Feature Engineering
Schedule: Hourly
Purpose: Generate features from raw data and store in features table
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import json
import logging

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=10)
}

dag = DAG(
    'feature_engineering',
    default_args=default_args,
    description='Generate features every hour',
    schedule_interval='0 * * * *',  # Every hour at minute 0
    catchup=False,
    tags=['feature-engineering', 'ml-pipeline']
)

def load_raw_data(**context):
    """
    Load raw data from PostgreSQL (last 7 days for lag features)
    """
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()

    # Load bike station status
    query_status = """
    SELECT
        bss.station_id,
        bss.timestamp,
        bss.bikes_available,
        bss.docks_available,
        bs.capacity,
        bs.latitude,
        bs.longitude
    FROM bike_station_status bss
    JOIN bike_stations bs ON bss.station_id = bs.station_id
    WHERE bss.timestamp >= NOW() - INTERVAL '7 days'
    ORDER BY bss.station_id, bss.timestamp
    """

    df_status = pd.read_sql_query(query_status, conn)

    # Load weather data
    query_weather = """
    SELECT
        timestamp,
        temperature,
        humidity,
        wind_speed,
        precipitation,
        weather_condition
    FROM weather_data
    WHERE timestamp >= NOW() - INTERVAL '7 days'
    ORDER BY timestamp
    """

    df_weather = pd.read_sql_query(query_weather, conn)

    conn.close()

    logging.info(f"Loaded {len(df_status)} station records and {len(df_weather)} weather records")

    # Store in XCom
    context['ti'].xcom_push(key='df_status', value=df_status.to_json(orient='records'))
    context['ti'].xcom_push(key='df_weather', value=df_weather.to_json(orient='records'))

def generate_features(**context):
    """
    Generate all features: temporal, lag, rolling, weather
    """
    # Load data from XCom
    df_status = pd.read_json(context['ti'].xcom_pull(key='df_status', task_ids='load_data'), orient='records')
    df_weather = pd.read_json(context['ti'].xcom_pull(key='df_weather', task_ids='load_data'), orient='records')

    # Parse timestamps
    df_status['timestamp'] = pd.to_datetime(df_status['timestamp'])
    df_weather['timestamp'] = pd.to_datetime(df_weather['timestamp'])

    # --- Temporal Features ---
    df_status['hour_of_day'] = df_status['timestamp'].dt.hour
    df_status['day_of_week'] = df_status['timestamp'].dt.dayofweek
    df_status['is_weekend'] = (df_status['day_of_week'] >= 5).astype(int)
    df_status['is_weekday'] = (df_status['day_of_week'] < 5).astype(int)
    df_status['month'] = df_status['timestamp'].dt.month
    df_status['is_morning_rush'] = ((df_status['hour_of_day'].between(7, 9)) & (df_status['is_weekday'] == 1)).astype(int)
    df_status['is_evening_rush'] = ((df_status['hour_of_day'].between(17, 19)) & (df_status['is_weekday'] == 1)).astype(int)

    # --- Lag Features ---
    df_status = df_status.sort_values(['station_id', 'timestamp'])

    df_status['bikes_lag_1h'] = df_status.groupby('station_id')['bikes_available'].shift(1)
    df_status['bikes_lag_24h'] = df_status.groupby('station_id')['bikes_available'].shift(24)
    df_status['bikes_lag_168h'] = df_status.groupby('station_id')['bikes_available'].shift(168)  # 1 week

    # --- Rolling Features ---
    df_status['bikes_rolling_mean_3h'] = df_status.groupby('station_id')['bikes_available'].rolling(3, min_periods=1).mean().reset_index(0, drop=True)
    df_status['bikes_rolling_std_3h'] = df_status.groupby('station_id')['bikes_available'].rolling(3, min_periods=1).std().reset_index(0, drop=True)

    # --- Weather Merge (nearest timestamp) ---
    df_status = pd.merge_asof(
        df_status.sort_values('timestamp'),
        df_weather.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta('1 hour')
    )

    # --- Fill NaN values ---
    df_status = df_status.fillna({
        'bikes_lag_1h': df_status['bikes_available'].mean(),
        'bikes_lag_24h': df_status['bikes_available'].mean(),
        'bikes_lag_168h': df_status['bikes_available'].mean(),
        'bikes_rolling_std_3h': 0,
        'temperature': 15.0,
        'humidity': 65.0,
        'wind_speed': 5.0,
        'precipitation': 0.0,
        'weather_condition': 'Clear'
    })

    logging.info(f"Generated features for {len(df_status)} records")

    # Store features as JSON (only last 24 hours for insert)
    recent_features = df_status[df_status['timestamp'] >= datetime.now() - timedelta(hours=24)]

    context['ti'].xcom_push(key='features', value=recent_features.to_json(orient='records'))

def insert_features(**context):
    """
    Insert features into features table (JSONB format)
    """
    features_json = context['ti'].xcom_pull(key='features', task_ids='generate_features')
    features_list = json.loads(features_json)

    if not features_list:
        logging.warning("No features to insert")
        return

    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO features (station_id, timestamp, feature_json, feature_version)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (station_id, timestamp, feature_version) DO NOTHING
    """

    feature_version = "v1.0"

    records = [
        (
            feature['station_id'],
            datetime.fromisoformat(feature['timestamp']),
            json.dumps({k: v for k, v in feature.items() if k not in ['station_id', 'timestamp']}),
            feature_version
        )
        for feature in features_list
    ]

    cursor.executemany(insert_query, records)
    inserted_count = cursor.rowcount
    conn.commit()

    logging.info(f"Inserted {inserted_count} feature records (version {feature_version})")

    cursor.close()
    conn.close()

# Tasks
task_load = PythonOperator(
    task_id='load_data',
    python_callable=load_raw_data,
    dag=dag
)

task_generate = PythonOperator(
    task_id='generate_features',
    python_callable=generate_features,
    dag=dag
)

task_insert = PythonOperator(
    task_id='insert_features',
    python_callable=insert_features,
    dag=dag
)

# Dependencies
task_load >> task_generate >> task_insert
```

**Key Features**:
- **7-day window**: Loads enough data to calculate lag features (up to 168 hours)
- **Temporal features**: Hour, day, weekend, rush hour indicators
- **Lag features**: 1h, 24h, 168h lags
- **Rolling features**: 3-hour rolling mean and std
- **Weather merge**: `merge_asof` for nearest timestamp join
- **JSONB storage**: Flexible schema for evolving features

---

## Step 5: Model Training DAG

### `airflow/dags/model_training_dag.py`

```python
"""
DAG: Model Training
Schedule: Daily at 2 AM
Purpose: Train XGBoost and LightGBM models, evaluate, and promote best to production
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import json
import logging
import mlflow
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import numpy as np
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=30)
}

dag = DAG(
    'model_training',
    default_args=default_args,
    description='Train models daily at 2 AM',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    tags=['ml-training', 'production']
)

# MLflow configuration
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def load_features_for_training(**context):
    """
    Load features from PostgreSQL for model training
    """
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = postgres_hook.get_conn()

    # Load last 30 days of features
    query = """
    SELECT
        station_id,
        timestamp,
        feature_json
    FROM features
    WHERE timestamp >= NOW() - INTERVAL '30 days'
    ORDER BY timestamp
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Expand JSONB into columns
    features_df = pd.json_normalize(df['feature_json'].apply(json.loads))

    # Add back station_id and timestamp
    features_df['station_id'] = df['station_id']
    features_df['timestamp'] = df['timestamp']

    logging.info(f"Loaded {len(features_df)} feature records with {len(features_df.columns)} columns")

    context['ti'].xcom_push(key='features_df', value=features_df.to_json(orient='records'))

def prepare_train_test_split(**context):
    """
    Create time-series train/val/test split (70/15/15)
    """
    features_json = context['ti'].xcom_pull(key='features_df', task_ids='load_features')
    df = pd.read_json(features_json, orient='records')

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    # Target variable
    target_col = 'bikes_available'

    # Feature columns (exclude non-features)
    exclude_cols = ['station_id', 'timestamp', 'bikes_available', 'docks_available', 'capacity', 'latitude', 'longitude']
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    X = df[feature_cols]
    y = df[target_col]

    # Time-series split
    n = len(df)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
    X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
    X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

    logging.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Store splits
    context['ti'].xcom_push(key='X_train', value=X_train.to_json(orient='records'))
    context['ti'].xcom_push(key='y_train', value=y_train.to_json(orient='records'))
    context['ti'].xcom_push(key='X_val', value=X_val.to_json(orient='records'))
    context['ti'].xcom_push(key='y_val', value=y_val.to_json(orient='records'))
    context['ti'].xcom_push(key='X_test', value=X_test.to_json(orient='records'))
    context['ti'].xcom_push(key='y_test', value=y_test.to_json(orient='records'))

def train_xgboost(**context):
    """
    Train XGBoost model and log to MLflow
    """
    # Load splits
    X_train = pd.read_json(context['ti'].xcom_pull(key='X_train', task_ids='prepare_split'), orient='records')
    y_train = pd.read_json(context['ti'].xcom_pull(key='y_train', task_ids='prepare_split'), orient='records', typ='series')
    X_val = pd.read_json(context['ti'].xcom_pull(key='X_val', task_ids='prepare_split'), orient='records')
    y_val = pd.read_json(context['ti'].xcom_pull(key='y_val', task_ids='prepare_split'), orient='records', typ='series')

    mlflow.set_experiment("bike-demand-forecasting")

    with mlflow.start_run(run_name=f"xgboost_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'objective': 'reg:squarederror',
            'random_state': 42
        }

        mlflow.log_params(params)

        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        # Evaluate
        y_pred = model.predict(X_val)

        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        mape = np.mean(np.abs((y_val - y_pred) / (y_val + 1e-10))) * 100

        metrics = {'rmse': rmse, 'mae': mae, 'r2_score': r2, 'mape': mape}

        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(model, "model")

        run_id = mlflow.active_run().info.run_id

        logging.info(f"XGBoost trained: RMSE={rmse:.3f}, MAE={mae:.3f}, R²={r2:.3f}")

        context['ti'].xcom_push(key='xgboost_metrics', value=metrics)
        context['ti'].xcom_push(key='xgboost_run_id', value=run_id)

def train_lightgbm(**context):
    """
    Train LightGBM model and log to MLflow
    """
    X_train = pd.read_json(context['ti'].xcom_pull(key='X_train', task_ids='prepare_split'), orient='records')
    y_train = pd.read_json(context['ti'].xcom_pull(key='y_train', task_ids='prepare_split'), orient='records', typ='series')
    X_val = pd.read_json(context['ti'].xcom_pull(key='X_val', task_ids='prepare_split'), orient='records')
    y_val = pd.read_json(context['ti'].xcom_pull(key='y_val', task_ids='prepare_split'), orient='records', typ='series')

    mlflow.set_experiment("bike-demand-forecasting")

    with mlflow.start_run(run_name=f"lightgbm_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        params = {
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'random_state': 42
        }

        mlflow.log_params(params)

        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.log_evaluation(period=0)])

        # Evaluate
        y_pred = model.predict(X_val)

        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        mape = np.mean(np.abs((y_val - y_pred) / (y_val + 1e-10))) * 100

        metrics = {'rmse': rmse, 'mae': mae, 'r2_score': r2, 'mape': mape}

        mlflow.log_metrics(metrics)
        mlflow.lightgbm.log_model(model, "model")

        run_id = mlflow.active_run().info.run_id

        logging.info(f"LightGBM trained: RMSE={rmse:.3f}, MAE={mae:.3f}, R²={r2:.3f}")

        context['ti'].xcom_push(key='lightgbm_metrics', value=metrics)
        context['ti'].xcom_push(key='lightgbm_run_id', value=run_id)

def promote_best_model(**context):
    """
    Compare models and promote best to Production
    """
    xgb_metrics = context['ti'].xcom_pull(key='xgboost_metrics', task_ids='train_xgboost')
    lgb_metrics = context['ti'].xcom_pull(key='lightgbm_metrics', task_ids='train_lightgbm')

    xgb_run_id = context['ti'].xcom_pull(key='xgboost_run_id', task_ids='train_xgboost')
    lgb_run_id = context['ti'].xcom_pull(key='lightgbm_run_id', task_ids='train_lightgbm')

    # Choose best based on RMSE
    if xgb_metrics['rmse'] < lgb_metrics['rmse']:
        best_run_id = xgb_run_id
        best_model_name = "XGBoost"
        best_metrics = xgb_metrics
    else:
        best_run_id = lgb_run_id
        best_model_name = "LightGBM"
        best_metrics = lgb_metrics

    logging.info(f"Best model: {best_model_name} with RMSE={best_metrics['rmse']:.3f}")

    # Register model
    model_uri = f"runs:/{best_run_id}/model"
    model_name = "bike-demand-forecaster"

    mlflow.register_model(model_uri, model_name)

    # Promote to Production
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions(f"name='{model_name}'")

    latest_version = max([int(v.version) for v in versions])

    client.transition_model_version_stage(
        name=model_name,
        version=latest_version,
        stage="Production"
    )

    logging.info(f"Model version {latest_version} promoted to Production")

# Tasks
task_load = PythonOperator(
    task_id='load_features',
    python_callable=load_features_for_training,
    dag=dag
)

task_split = PythonOperator(
    task_id='prepare_split',
    python_callable=prepare_train_test_split,
    dag=dag
)

task_train_xgb = PythonOperator(
    task_id='train_xgboost',
    python_callable=train_xgboost,
    dag=dag
)

task_train_lgb = PythonOperator(
    task_id='train_lightgbm',
    python_callable=train_lightgbm,
    dag=dag
)

task_promote = PythonOperator(
    task_id='promote_best_model',
    python_callable=promote_best_model,
    dag=dag
)

# Dependencies
task_load >> task_split >> [task_train_xgb, task_train_lgb] >> task_promote
```

**Key Features**:
- **Daily training**: Runs at 2 AM to train on fresh data
- **Parallel training**: XGBoost and LightGBM train simultaneously
- **Model comparison**: Automatically promotes best model (lowest RMSE)
- **MLflow integration**: Logs params, metrics, and models
- **Model registry**: Registers and transitions to Production stage

---

## Step 6: Airflow Configuration

### Setting up Postgres Connection

1. **Access Airflow UI**: `http://localhost:8080`
2. **Login**: `admin` / `admin`
3. **Admin → Connections → Add**
4. **Configure**:
   - Conn Id: `postgres_default`
   - Conn Type: `Postgres`
   - Host: `postgres`
   - Schema: `bike_demand_db`
   - Login: `postgres`
   - Password: `postgres`
   - Port: `5432`

---

## Step 7: Testing DAGs

### 1. Start Airflow

```bash
cd infrastructure
docker-compose up -d airflow-webserver airflow-scheduler
```

### 2. Access UI

Open `http://localhost:8080` and login with `admin/admin`

### 3. Trigger Data Ingestion DAG

- Navigate to **DAGs**
- Find `data_ingestion`
- Click **Play** button (trigger DAG)
- Monitor task progress in Graph View

### 4. Check Logs

- Click on a task in Graph View
- Click **Log** button
- Verify successful execution

### 5. Verify Data in PostgreSQL

```bash
docker exec -it infrastructure-postgres-1 psql -U postgres -d bike_demand_db -c "SELECT COUNT(*) FROM bike_station_status;"
```

Expected: Rows inserted

---

## Monitoring DAG Runs

### Graph View

Shows task dependencies and status:
- **Green**: Success
- **Red**: Failed
- **Yellow**: Running
- **Grey**: Not started

### Tree View

Shows historical runs:
- Columns = DAG runs
- Rows = Tasks
- Colors indicate success/failure

### Gantt Chart

Shows task duration over time (useful for optimizing)

---

## Common Issues & Fixes

### Issue: DAG not appearing in UI

**Cause**: Syntax error in DAG file

**Fix**:
```bash
# Check scheduler logs
docker logs infrastructure-airflow-scheduler-1

# Validate DAG
docker exec -it infrastructure-airflow-scheduler-1 airflow dags list
```

### Issue: Task fails with "Connection not found"

**Cause**: `postgres_default` connection not configured

**Fix**: Add connection in Airflow UI (see Step 6)

### Issue: Import errors in DAG

**Cause**: Missing dependencies in Airflow container

**Fix**:
```dockerfile
# Add to docker/airflow/Dockerfile
RUN pip install pandas requests sqlalchemy
```

Rebuild:
```bash
docker-compose build airflow-webserver airflow-scheduler
docker-compose up -d airflow-webserver airflow-scheduler
```

### Issue: XCom size limit exceeded

**Cause**: Passing large DataFrames via XCom (default limit: 1 MB)

**Fix**: Use file-based storage or database for large datasets:
```python
# Instead of XCom, save to temp table
df.to_sql('temp_features', conn, if_exists='replace')

# Load in next task
df = pd.read_sql_table('temp_features', conn)
```

---

## Interview Talking Points

1. **"I automated the entire ML pipeline using Apache Airflow with 4 DAGs running at different intervals - data ingestion every 15 minutes, feature engineering hourly, and model training daily"**

2. **"I implemented retry logic with exponential backoff and idempotent operations using ON CONFLICT to ensure pipeline reliability"**

3. **"The feature engineering DAG uses time-series windows (7 days) to calculate lag features while preventing data leakage"**

4. **"I built a model training DAG that trains XGBoost and LightGBM in parallel, compares performance, and automatically promotes the best model to production via MLflow"**

5. **"The pipeline uses XCom for passing small data between tasks and PostgreSQL temp tables for larger datasets to avoid XCom size limits"**

---

## Summary

You've built a fully automated ML pipeline with:

✅ **Data Ingestion DAG** (15-min) - Fetch from Citi Bike API
✅ **Weather Enrichment DAG** (30-min) - OpenWeatherMap integration
✅ **Feature Engineering DAG** (hourly) - 25+ features generated
✅ **Model Training DAG** (daily) - Auto-trains and promotes best model
✅ **Retry Logic** - 3 retries with exponential backoff
✅ **Idempotent Operations** - ON CONFLICT prevents duplicates
✅ **MLflow Integration** - Experiment tracking and model registry
✅ **Visual Monitoring** - Airflow UI for DAG monitoring

**Next Chapter**: [Chapter 9: Monitoring & Observability](09-monitoring.md) - Add data drift detection, performance monitoring, and alerting with Evidently AI and Prometheus.
