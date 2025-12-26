# 🚀 Complete Production Setup Guide

**Status: Working & Tested (December 2025)**

This guide documents the **exact working configuration** for the Level 2 MLOps production system.

---

## ✅ Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ with dependencies installed
- Ports available: 5000 (MLflow), 5432 (PostgreSQL), 8000 (API), 8080 (Airflow), 8501 (Dashboard)

---

## 🎯 Quick Start (Complete Working System)

### Step 1: Start Infrastructure (2 min)

```bash
# Start PostgreSQL and MLflow
docker-compose -f infrastructure/docker-compose.yml up -d postgres mlflow

# Wait for services
sleep 30

# Verify
docker-compose -f infrastructure/docker-compose.yml ps
```

**Expected Output:**
```
NAME                   STATUS              PORTS
bike_demand_mlflow     running (healthy)   0.0.0.0:5000->5000/tcp
bike_demand_postgres   running (healthy)   0.0.0.0:5432->5432/tcp
```

---

### Step 2: Start Airflow (3 min)

```bash
# Initialize Airflow (first time only)
docker-compose -f infrastructure/docker-compose.yml up -d airflow-init

# Wait for initialization
sleep 45

# Start Airflow webserver and scheduler
docker-compose -f infrastructure/docker-compose.yml up -d airflow-webserver airflow-scheduler

# Verify
docker-compose -f infrastructure/docker-compose.yml ps airflow-scheduler airflow-webserver
```

**Access Airflow UI:**
- URL: http://localhost:8080
- Username: `airflow`
- Password: `airflow`

---

### Step 3: Trigger Data Collection DAGs (5 min)

**IMPORTANT:** DAGs must run in this order (dependencies are configured):

```bash
# 1. Collect station information (creates bike_stations table)
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger citi_bike_data_ingestion

# Wait 2 minutes for station data

# 2. Collect weather data
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger weather_enrichment

# Wait 1 minute
```

**Verify Data Collection:**
```bash
docker-compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c \
  "SELECT COUNT(*) as stations FROM bike_stations;
   SELECT COUNT(*) as statuses FROM bike_station_status;
   SELECT COUNT(*) as weather FROM weather_data;"
```

**Expected Result:**
- Stations: ~2300
- Statuses: ~2300
- Weather: 1+

---

### Step 4: Register Initial Model to Docker MLflow (2 min)

**Option A: Using Docker Training Container (Recommended)**

```bash
# Build training image
docker build -f docker/training/Dockerfile -t bike-demand-trainer:latest .

# Run training to register model
docker run --rm \
  --network host \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-trainer:latest
```

**Expected Output:**
```
✅ Model version 1 promoted to Production!
MLflow UI: http://localhost:5000
Model: bike-demand-forecasting v1
```

**Option B: Using Python Script (Host)**

```bash
python scripts/quick_register_model.py
```

**Verify Model in MLflow:**
```bash
curl -s "http://localhost:5000/api/2.0/mlflow/registered-models/get?name=bike-demand-forecasting" \
  | python -m json.tool | grep -E "(name|version|current_stage)"
```

---

### Step 5: Start API Server (1 min)

**Note:** Currently best run on host due to artifact path issues with Docker MLflow.

```bash
# Start API
uvicorn src.serving.api.main:app --host 0.0.0.0 --port 8000 &

# Wait for startup
sleep 5

# Verify health
curl http://localhost:8000/health/detailed | python -m json.tool
```

**Expected Response:**
```json
{
  "status": "healthy",
  "components": {
    "api": {"status": "healthy"},
    "database": {"status": "healthy"},
    "mlflow": {"status": "healthy"}
  }
}
```

**API Documentation:** http://localhost:8000/docs

---

### Step 6: Start Dashboard (1 min)

```bash
streamlit run dashboard/app.py --server.port 8501 &
```

**Access Dashboard:** http://localhost:8501

---

## 🔧 Key Configuration Details (What We Fixed)

### 1. Airflow Database Connection

**Problem:** Airflow containers couldn't connect to PostgreSQL
**Solution:** Added environment variables to `infrastructure/docker-compose.yml`:

```yaml
  airflow-scheduler:
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_DATABASE: bike_demand_db
      MLFLOW_TRACKING_URI: http://mlflow:5000
      WEATHER_API_KEY: ${WEATHER_API_KEY}
```

### 2. Data Ingestion DAG Task Dependencies

**Problem:** Station status inserted before station information (FK violation)
**Solution:** Updated `airflow/dags/data_ingestion_dag.py`:

```python
# BEFORE (parallel - wrong):
start >> [task_collect_station_info, task_collect_station_status]

# AFTER (sequential - correct):
start >> task_collect_station_info >> task_collect_station_status
```

### 3. MLflow Artifact Access

**Problem:** Models stored in Docker volume `/mlflow` not accessible from host
**Solution:** Use `--network host` for training container OR deploy API in Docker

### 4. Docker Training Infrastructure

**Created:** `docker/training/Dockerfile` and `scripts/quick_register_model.py`
**Purpose:** Train and register models entirely within Docker ecosystem

---

## 📊 System Architecture (As Deployed)

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Containers                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │PostgreSQL│  │  MLflow  │  │     Airflow         │  │
│  │  :5432   │  │  :5000   │  │  webserver :8080    │  │
│  │          │  │          │  │  scheduler          │  │
│  └─────┬────┘  └────┬─────┘  └──────────┬──────────┘  │
│        │            │                    │              │
└────────┼────────────┼────────────────────┼──────────────┘
         │            │                    │
    ┌────▼────────────▼────────────────────▼─────┐
    │            Host Machine                     │
    │  ┌──────────┐          ┌──────────┐       │
    │  │ FastAPI  │          │Streamlit │       │
    │  │  :8000   │          │  :8501   │       │
    │  └──────────┘          └──────────┘       │
    └─────────────────────────────────────────────┘
```

---

## 🔄 Automated Workflows (After Setup)

### Data Collection (Every 15 minutes)
```
citi_bike_data_ingestion DAG:
  1. Collect station information
  2. Collect station status
  3. Validate data quality
  4. Log metrics
```

### Weather Enrichment (Every 30 minutes)
```
weather_enrichment DAG:
  1. Fetch NYC weather from OpenWeatherMap
  2. Store in PostgreSQL
  3. Validate and log
```

### Feature Engineering (Every hour)
```
feature_engineering DAG:
  1. Extract bike + weather data
  2. Generate temporal features
  3. Generate lag features
  4. Generate rolling features
  5. Save to features table
```

### Model Training (Daily at 2 AM)
```
model_training DAG:
  1. Validate feature availability (>100 records)
  2. Train XGBoost, LightGBM, CatBoost
  3. Compare models
  4. Register best model to MLflow
  5. Promote to Production if RMSE < 10
  6. Archive old versions
```

---

## ✅ Verification Checklist

Run these commands to verify everything is working:

```bash
# 1. Check Docker containers
docker-compose -f infrastructure/docker-compose.yml ps

# 2. Check PostgreSQL data
docker-compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c \
  "SELECT
    (SELECT COUNT(*) FROM bike_stations) as stations,
    (SELECT COUNT(*) FROM bike_station_status) as statuses,
    (SELECT COUNT(*) FROM weather_data) as weather,
    (SELECT COUNT(*) FROM features) as features;"

# 3. Check MLflow model
curl -s "http://localhost:5000/api/2.0/mlflow/registered-models/get?name=bike-demand-forecasting" \
  | python -m json.tool | grep -E "(version|current_stage)"

# 4. Check Airflow DAGs
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags list | grep -E "(citi_bike|weather|feature|model)"

# 5. Check API health
curl http://localhost:8000/health/detailed | python -m json.tool

# 6. Test prediction
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c",
    "timestamp": "2025-12-26T17:00:00Z",
    "features": {
      "hour": 17,
      "day_of_week": 3,
      "temperature": 15.5,
      "humidity": 65.0
    }
  }'
```

---

## 🚨 Troubleshooting

### Issue: Airflow DAG fails with database connection error

**Symptoms:**
```
psycopg2.OperationalError: connection to server at "localhost" refused
```

**Fix:**
Ensure Airflow containers have correct environment variables:
```bash
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  printenv | grep -E "^DB_"
```

Should show:
```
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_DATABASE=bike_demand_db
```

If missing, update `infrastructure/docker-compose.yml` and restart:
```bash
docker-compose -f infrastructure/docker-compose.yml up -d --force-recreate \
  airflow-scheduler airflow-webserver
```

---

### Issue: Data ingestion fails with FK constraint violation

**Symptoms:**
```
ForeignKeyViolation: insert or update on table "bike_station_status"
violates foreign key constraint
```

**Fix:**
The `data_ingestion_dag.py` must run tasks sequentially:
1. First collect station information (populates `bike_stations`)
2. Then collect station status (references `bike_stations`)

Check task dependencies at the end of `airflow/dags/data_ingestion_dag.py`:
```python
start >> task_collect_station_info >> task_collect_station_status
```

---

### Issue: Model not loading from MLflow

**Symptoms:**
```
OSError: No such file or directory: '/mlflow/artifacts/...'
```

**Root Cause:**
Models registered inside Docker have artifact paths that aren't accessible from host.

**Fix Option 1 - Train with host network:**
```bash
docker run --rm \
  --network host \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-trainer:latest
```

**Fix Option 2 - Deploy API in Docker:**
Add `holidays` package to `docker/api/Dockerfile` and run:
```bash
docker-compose -f infrastructure/docker-compose.yml up -d api
```

---

## 📈 Production Readiness Timeline

| Day | Data Collected | Model Quality | Status |
|-----|---------------|---------------|---------|
| Day 1 | 96 snapshots | Demo model | ⚠️ Basic |
| Day 3 | 288 snapshots | Limited features | ⚙️ Functional |
| Day 7 | 672 snapshots | Good features | ✅ Production-ready |
| Day 30 | 2,880 snapshots | Excellent | 🚀 Optimal |

**Current Status (Day 1):**
- ✅ Infrastructure: Complete
- ✅ Data Collection: Active
- ✅ Model Registry: 1 model registered
- ⚠️ Features: Limited (need more time-series data)
- ⚙️ API/Dashboard: Working with demo model

---

## 🎯 Next Steps

1. **Let DAGs run for 7 days** to collect sufficient time-series data
2. **Monitor Airflow UI** (http://localhost:8080) for DAG health
3. **Check MLflow UI** (http://localhost:5000) for model experiments
4. **After 7 days:** Trigger `model_training` DAG for production-quality model
5. **Set up alerts:** Configure Slack/email for DAG failures
6. **Add monitoring:** Prometheus + Grafana dashboards

---

## 🎊 Success Criteria Met

- [x] All Docker containers running and healthy
- [x] PostgreSQL storing bike station + weather data
- [x] MLflow tracking experiments and model registry
- [x] Airflow DAGs automated and configured
- [x] Model registered to MLflow (v1 in Production)
- [x] API serving predictions (with demo model)
- [x] System following Level 2 MLOps maturity

**Congratulations! You have a working Level 2 MLOps system!** 🎉

---

## 📚 References

- **Original Guide:** [docs/START_PRODUCTION.md](START_PRODUCTION.md)
- **MLflow UI:** http://localhost:5000
- **Airflow UI:** http://localhost:8080
- **API Docs:** http://localhost:8000/docs
- **Dashboard:** http://localhost:8501

