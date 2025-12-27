# Chapter 2: Database & Infrastructure

## Overview

In this chapter, you'll:
- Understand the database schema design
- Learn why PostgreSQL for time-series data
- Start all infrastructure services with Docker Compose
- Create the database schema
- Verify the database is working

**Estimated Time**: 2 hours

## Why PostgreSQL?

### Requirements for ML Systems
Our system needs to:
- Store **time-series data** (bike demand over time)
- Support **high write throughput** (data every 15 minutes)
- Handle **complex queries** (JOIN across tables)
- Store **JSON/JSONB** (flexible feature storage)
- Provide **ACID guarantees** (data consistency)

###

 PostgreSQL Advantages
- ✅ **JSONB support**: Store features as JSON with indexing
- ✅ **Time-series functions**: DATE_TRUNC, window functions
- ✅ **Mature ecosystem**: Well-tested, production-ready
- ✅ **Free and open-source**: No licensing costs
- ✅ **Great performance**: Handles millions of rows easily
- ✅ **Strong typing**: Prevents data quality issues

## Database Schema Design

### Core Principle: Separation of Concerns

We separate data into layers:
1. **Raw Data Layer**: As received from APIs
2. **Processed Data Layer**: Cleaned and validated
3. **Feature Layer**: Engineered features for ML
4. **Prediction Layer**: Model outputs
5. **Metadata Layer**: Model performance, data quality

### Table Structure

#### 1. `bike_stations` - Station Master Data
```sql
CREATE TABLE bike_stations (
    station_id VARCHAR(50) PRIMARY KEY,    -- Unique station identifier
    name VARCHAR(255) NOT NULL,            -- Station name
    latitude DECIMAL(10, 8) NOT NULL,      -- GPS coordinates
    longitude DECIMAL(11, 8) NOT NULL,
    capacity INTEGER NOT NULL,              -- Total docks at station
    is_active BOOLEAN DEFAULT TRUE,         -- Station operational?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Why this design?**
- `station_id` as VARCHAR allows for future non-numeric IDs
- DECIMAL for coordinates ensures precision (8 decimal places = ~1mm accuracy)
- `is_active` allows soft-deletes (never remove historical data)
- Timestamps track data lineage

#### 2. `bike_station_status` - Time-Series Demand Data
```sql
CREATE TABLE bike_station_status (
    id SERIAL PRIMARY KEY,                  -- Auto-incrementing ID
    station_id VARCHAR(50) NOT NULL,        -- FK to bike_stations
    timestamp TIMESTAMP NOT NULL,            -- When was this measured?
    bikes_available INTEGER NOT NULL,        -- Bikes ready to rent
    docks_available INTEGER NOT NULL,        -- Empty docks
    bikes_disabled INTEGER DEFAULT 0,        -- Broken bikes
    docks_disabled INTEGER DEFAULT 0,        -- Broken docks
    is_installed BOOLEAN DEFAULT TRUE,
    is_renting BOOLEAN DEFAULT TRUE,
    is_returning BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX idx_bike_station_status_station_id ON bike_station_status (station_id);
CREATE INDEX idx_bike_station_status_timestamp ON bike_station_status (timestamp DESC);
CREATE INDEX idx_bike_station_status_station_timestamp ON bike_station_status (station_id, timestamp DESC);
```

**Why this design?**
- Composite index `(station_id, timestamp)` speeds up "get latest status for station X"
- `timestamp DESC` index enables fast "get most recent N records"
- Foreign key ensures referential integrity
- Separate `bikes_disabled` from `bikes_available` for data quality monitoring

#### 3. `weather_data` - Weather Enrichment
```sql
CREATE TABLE weather_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    location_id VARCHAR(50),                 -- Can support multiple cities
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    temperature DECIMAL(5, 2),               -- Celsius
    feels_like DECIMAL(5, 2),
    humidity INTEGER,                        -- Percentage
    wind_speed DECIMAL(5, 2),                -- m/s
    precipitation DECIMAL(5, 2) DEFAULT 0,   -- mm
    weather_condition VARCHAR(50),           -- 'Clear', 'Rain', etc.
    weather_description VARCHAR(255),
    pressure INTEGER,                        -- hPa
    visibility INTEGER,                      -- meters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_weather_data_timestamp ON weather_data (timestamp DESC);
CREATE INDEX idx_weather_data_location ON weather_data (latitude, longitude);
```

**Why this design?**
- Separate from bike data (different update frequency)
- Can join on timestamp (hourly alignment)
- Supports multiple locations for multi-city expansion

#### 4. `features` - Engineered Features for ML
```sql
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    feature_json JSONB NOT NULL,             -- All features as JSON
    feature_version VARCHAR(20) NOT NULL,    -- Track feature schema changes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE,
    UNIQUE (station_id, timestamp, feature_version)  -- Enable upserts
);

-- Indexes
CREATE INDEX idx_features_station_id ON features (station_id);
CREATE INDEX idx_features_timestamp ON features (timestamp DESC);
CREATE INDEX idx_features_version ON features (feature_version);
CREATE INDEX idx_features_json ON features USING GIN (feature_json);  -- JSONB index
```

**Why JSONB for features?**
- **Flexibility**: Add features without schema migrations
- **Versioning**: Store multiple feature versions side-by-side
- **Performance**: GIN index allows fast JSON queries
- **Reproducibility**: Features stored exactly as fed to model

**Example feature_json:**
```json
{
  "hour_of_day": 14,
  "day_of_week": 3,
  "is_weekend": 0,
  "is_morning_rush": 0,
  "is_evening_rush": 0,
  "bikes_lag_1h": 15,
  "bikes_lag_6h": 12,
  "bikes_lag_24h": 18,
  "bikes_rolling_mean_3h": 14.5,
  "bikes_rolling_std_3h": 2.1,
  "temperature": 22.5,
  "humidity": 65,
  "is_holiday": 0
}
```

#### 5. `predictions` - Model Outputs
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMP NOT NULL,     -- When prediction is for
    predicted_demand DECIMAL(8, 2) NOT NULL,    -- Predicted bikes available
    model_version VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    confidence_interval_lower DECIMAL(8, 2),    -- 95% CI lower bound
    confidence_interval_upper DECIMAL(8, 2),    -- 95% CI upper bound
    prediction_horizon_hours INTEGER DEFAULT 1, -- How far ahead?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When prediction made
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE
);

CREATE INDEX idx_predictions_station_id ON predictions (station_id);
CREATE INDEX idx_predictions_timestamp ON predictions (prediction_timestamp DESC);
CREATE INDEX idx_predictions_model ON predictions (model_name, model_version);
CREATE INDEX idx_predictions_created_at ON predictions (created_at DESC);
```

**Why separate predictions table?**
- Track prediction drift (predicted vs actual)
- Support A/B testing (compare model versions)
- Historical analysis of model performance

#### 6. `model_performance` - Model Metrics Tracking
```sql
CREATE TABLE model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    evaluation_date DATE NOT NULL,
    rmse DECIMAL(8, 4),                      -- Root Mean Squared Error
    mae DECIMAL(8, 4),                       -- Mean Absolute Error
    mape DECIMAL(8, 4),                      -- Mean Absolute Percentage Error
    r2_score DECIMAL(8, 4),                  -- R-squared
    data_drift_score DECIMAL(8, 4),          -- Evidently AI drift metric
    prediction_drift_score DECIMAL(8, 4),
    metadata JSONB,                          -- Additional metrics
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_performance_model ON model_performance (model_name, model_version);
CREATE INDEX idx_model_performance_date ON model_performance (evaluation_date DESC);
```

**Why track performance over time?**
- Detect model degradation
- Trigger retraining when RMSE increases
- Compare models objectively

## Starting the Infrastructure

### Step 1: Navigate to Infrastructure
```bash
cd infrastructure
```

### Step 2: Understand Docker Compose

Open `docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: bike_demand_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: bike_demand_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bike_demand_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    container_name: bike_demand_mlflow
    ports:
      - "5000:5000"
    command: mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://postgres:postgres@postgres:5432/mlflow --default-artifact-root /mlflow/artifacts
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - mlflow_data:/mlflow
    networks:
      - bike_demand_network

volumes:
  postgres_data:
  mlflow_data:

networks:
  bike_demand_network:
    driver: bridge
```

**Key Concepts:**
- **Services**: Individual containers (postgres, mlflow, etc.)
- **Volumes**: Persistent storage (survives container restarts)
- **Networks**: Allow containers to communicate
- **Health Checks**: Ensure service is ready before dependents start

### Step 3: Start Infrastructure

```bash
# Start all services
docker compose up -d

# Explanation:
# up = start services
# -d = detached mode (run in background)
```

**Expected Output:**
```
[+] Running 3/3
 ✔ Network infrastructure_bike_demand_network  Created
 ✔ Container bike_demand_postgres              Started
 ✔ Container bike_demand_mlflow                Started
```

### Step 4: Verify Services Are Running

```bash
# Check container status
docker compose ps

# Should show:
# NAME                    STATUS              PORTS
# bike_demand_postgres    Up (healthy)        0.0.0.0:5432->5432/tcp
# bike_demand_mlflow      Up                  0.0.0.0:5000->5000/tcp
```

### Step 5: Check Logs

```bash
# View PostgreSQL logs
docker compose logs postgres

# View MLflow logs
docker compose logs mlflow

# Follow logs in real-time
docker compose logs -f
```

## Creating the Database Schema

### Step 1: Verify PostgreSQL is Ready

```bash
# Wait for PostgreSQL health check
docker compose exec postgres pg_isready -U postgres

# Should output: /var/run/postgresql:5432 - accepting connections
```

### Step 2: Create Schema from SQL File

```bash
# Execute schema.sql inside the container
docker compose exec -T postgres psql -U postgres -d bike_demand_db < postgres/schema.sql

# Explanation:
# exec = run command in container
# -T = no pseudo-TTY (for piping input)
# psql = PostgreSQL client
# -U postgres = connect as user 'postgres'
# -d bike_demand_db = use database 'bike_demand_db'
# < postgres/schema.sql = pipe file contents
```

**Expected Output:**
```
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
...
CREATE TRIGGER
CREATE VIEW
```

### Step 3: Verify Schema Creation

```bash
# List all tables
docker compose exec postgres psql -U postgres -d bike_demand_db -c "\dt"

# Should show:
#  Schema |        Name         | Type  |  Owner
# --------+---------------------+-------+----------
#  public | bike_stations       | table | postgres
#  public | bike_station_status | table | postgres
#  public | weather_data        | table | postgres
#  public | features            | table | postgres
#  public | predictions         | table | postgres
#  public | model_performance   | table | postgres
```

### Step 4: Explore the Schema

```bash
# Describe bike_stations table
docker compose exec postgres psql -U postgres -d bike_demand_db -c "\d bike_stations"

# Show indexes
docker compose exec postgres psql -U postgres -d bike_demand_db -c "\di"

# Show views
docker compose exec postgres psql -U postgres -d bike_demand_db -c "\dv"
```

## Database Views for Analytics

The schema includes helpful views:

### 1. `latest_station_status` - Most Recent Data
```sql
CREATE OR REPLACE VIEW latest_station_status AS
SELECT DISTINCT ON (station_id)
    bss.station_id,
    bs.name,
    bs.latitude,
    bs.longitude,
    bs.capacity,
    bss.bikes_available,
    bss.docks_available,
    bss.timestamp,
    (bss.bikes_available::DECIMAL / NULLIF(bs.capacity, 0)) * 100 AS occupancy_percentage
FROM bike_station_status bss
JOIN bike_stations bs ON bss.station_id = bs.station_id
WHERE bs.is_active = TRUE
ORDER BY bss.station_id, bss.timestamp DESC;
```

**Use Case**: Dashboard showing current system state

### 2. `hourly_demand` - Aggregated Statistics
```sql
CREATE OR REPLACE VIEW hourly_demand AS
SELECT
    station_id,
    DATE_TRUNC('hour', timestamp) AS hour,
    AVG(bikes_available) AS avg_bikes_available,
    MIN(bikes_available) AS min_bikes_available,
    MAX(bikes_available) AS max_bikes_available,
    STDDEV(bikes_available) AS stddev_bikes_available,
    COUNT(*) AS num_observations
FROM bike_station_status
GROUP BY station_id, DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;
```

**Use Case**: Hourly demand patterns for visualization

## Testing the Database

### Step 1: Insert Test Station

```bash
docker compose exec postgres psql -U postgres -d bike_demand_db << 'SQL'
INSERT INTO bike_stations (station_id, name, latitude, longitude, capacity, is_active)
VALUES ('test-001', 'Test Station', 40.7589, -73.9851, 30, true);
SQL
```

### Step 2: Insert Test Status

```bash
docker compose exec postgres psql -U postgres -d bike_demand_db << 'SQL'
INSERT INTO bike_station_status (station_id, timestamp, bikes_available, docks_available)
VALUES ('test-001', NOW(), 15, 15);
SQL
```

### Step 3: Query Data

```bash
# View test data
docker compose exec postgres psql -U postgres -d bike_demand_db -c "SELECT * FROM bike_stations WHERE station_id = 'test-001';"

# Use the view
docker compose exec postgres psql -U postgres -d bike_demand_db -c "SELECT * FROM latest_station_status WHERE station_id = 'test-001';"
```

### Step 4: Clean Up Test Data

```bash
docker compose exec postgres psql -U postgres -d bike_demand_db << 'SQL'
DELETE FROM bike_stations WHERE station_id = 'test-001';
SQL
```

## Connecting with a GUI Tool (Optional)

### Option 1: pgAdmin
1. Download from [pgadmin.org](https://www.pgadmin.org/)
2. Add server:
   - Host: localhost
   - Port: 5432
   - Database: bike_demand_db
   - Username: postgres
   - Password: postgres

### Option 2: DBeaver
1. Download from [dbeaver.io](https://dbeaver.io/)
2. Create connection to PostgreSQL
3. Use same credentials

### Option 3: VS Code Extension
1. Install "PostgreSQL" extension
2. Connect with same credentials

## MLflow Setup

### Step 1: Access MLflow UI

```bash
# Open in browser
open http://localhost:5000

# Or manually navigate to:
# http://localhost:5000
```

You should see the MLflow UI with no experiments yet.

### Step 2: Verify MLflow Backend

```bash
# Check MLflow logs
docker compose logs mlflow

# Should show:
# [INFO] Starting gunicorn 20.1.0
# [INFO] Listening at: http://0.0.0.0:5000
```

## Troubleshooting

### PostgreSQL Won't Start

**Check logs:**
```bash
docker compose logs postgres
```

**Common issues:**
- Port 5432 already in use
- Insufficient disk space
- Corrupted volume

**Solution:**
```bash
# Stop all containers
docker compose down

# Remove volumes
docker compose down -v

# Restart
docker compose up -d
```

### Can't Connect to Database

**Verify network:**
```bash
docker network ls
# Should show: infrastructure_bike_demand_network

docker network inspect infrastructure_bike_demand_network
# Should show both postgres and mlflow containers
```

### MLflow Can't Connect to PostgreSQL

**Check depends_on in docker-compose.yml:**
```yaml
mlflow:
  depends_on:
    postgres:
      condition: service_healthy
```

**Verify health check:**
```bash
docker compose ps
# postgres should show "healthy" in STATUS
```

## Summary

### What You Learned

✅ **Database Design**: Time-series schema, normalization, indexing
✅ **PostgreSQL Features**: JSONB, indexes, views, triggers
✅ **Docker Compose**: Multi-service orchestration
✅ **Infrastructure as Code**: Reproducible setup
✅ **Data Modeling**: Separation of concerns, versioning

### Database Schema Summary

| Table | Purpose | Records (Production) |
|-------|---------|---------------------|
| `bike_stations` | Station master data | ~4,500 |
| `bike_station_status` | Time-series demand | Millions |
| `weather_data` | Weather enrichment | Hundreds of thousands |
| `features` | Engineered features | Millions |
| `predictions` | Model outputs | Millions |
| `model_performance` | Model metrics | Thousands |

### Key Takeaways

1. **JSONB is powerful** for flexible ML feature storage
2. **Indexes are critical** for query performance
3. **Separation of raw/processed data** enables debugging
4. **Foreign keys ensure data integrity**
5. **Docker Compose makes infrastructure reproducible**

## Next Steps

Now that your database is ready, head to **[Chapter 3: Data Collection Pipeline](03-data-collection.md)** to start ingesting real bike-sharing data!

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
