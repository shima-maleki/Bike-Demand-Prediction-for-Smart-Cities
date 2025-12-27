# Chapter 13: Troubleshooting Guide

## Overview

This guide covers common issues you might encounter and their solutions. Use this as a reference when things don't work as expected.

## Table of Contents

1. [Docker Issues](#docker-issues)
2. [Database Issues](#database-issues)
3. [API Issues](#api-issues)
4. [Dashboard Issues](#dashboard-issues)
5. [Airflow Issues](#airflow-issues)
6. [Model Training Issues](#model-training-issues)
7. [Performance Issues](#performance-issues)
8. [Data Quality Issues](#data-quality-issues)

---

## Docker Issues

### Issue: "Cannot connect to Docker daemon"

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solutions:**
1. **Start Docker Desktop**
   ```bash
   # macOS: Open Docker Desktop from Applications
   # Windows: Start Docker Desktop from Start Menu
   # Linux: Start Docker service
   sudo systemctl start docker
   ```

2. **Verify Docker is running**
   ```bash
   docker ps
   # Should show running containers or empty table
   ```

3. **Add user to docker group (Linux only)**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

---

### Issue: "Port already in use"

**Symptoms:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use
```

**Solutions:**

1. **Find what's using the port**
   ```bash
   # macOS/Linux
   lsof -i :5432

   # Windows
   netstat -ano | findstr :5432
   ```

2. **Stop the conflicting service**
   ```bash
   # Example: Kill PostgreSQL on macOS
   brew services stop postgresql
   ```

3. **Change port in docker-compose.yml**
   ```yaml
   services:
     postgres:
       ports:
         - "5433:5432"  # Changed from 5432:5432
   ```

**Common port conflicts:**
- 5432: PostgreSQL
- 8000: FastAPI / other web servers
- 5000: MLflow / Flask apps
- 8080: Airflow / Jenkins
- 8501: Streamlit / other apps

---

### Issue: "docker compose: command not found"

**Symptoms:**
```bash
docker compose up
# zsh: command not found: compose
```

**Solutions:**

1. **Check Docker version**
   ```bash
   docker --version
   # Need Docker 20.10+ for 'docker compose'
   ```

2. **Use docker-compose (older versions)**
   ```bash
   docker-compose up -d
   # Note: hyphen instead of space
   ```

3. **Upgrade Docker Desktop**
   - Download latest from [docker.com](https://www.docker.com/products/docker-desktop/)

---

### Issue: "No space left on device"

**Symptoms:**
```
Error: No space left on device
```

**Solutions:**

1. **Clean up Docker resources**
   ```bash
   # Remove unused containers
   docker container prune -f

   # Remove unused images
   docker image prune -a -f

   # Remove unused volumes
   docker volume prune -f

   # Remove everything (CAREFUL!)
   docker system prune -a --volumes -f
   ```

2. **Check disk usage**
   ```bash
   docker system df
   ```

3. **Increase Docker disk limit**
   - Docker Desktop → Settings → Resources → Disk image size

---

## Database Issues

### Issue: "Database connection refused"

**Symptoms:**
```python
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solutions:**

1. **Verify PostgreSQL is running**
   ```bash
   docker compose ps postgres
   # Should show "Up (healthy)"
   ```

2. **Check logs**
   ```bash
   docker compose logs postgres
   # Look for errors
   ```

3. **Wait for health check**
   ```bash
   # PostgreSQL takes 10-30 seconds to start
   docker compose exec postgres pg_isready -U postgres
   # Should output: "accepting connections"
   ```

4. **Verify connection details in .env**
   ```bash
   cat .env | grep DB_
   # DB_HOST=bike_demand_postgres  (container name, not localhost!)
   # DB_PORT=5432
   # DB_USER=postgres
   # DB_PASSWORD=postgres
   # DB_DATABASE=bike_demand_db
   ```

---

### Issue: "Database does not exist"

**Symptoms:**
```
psycopg2.OperationalError: FATAL: database "bike_demand_db" does not exist
```

**Solutions:**

1. **Create database**
   ```bash
   docker compose exec postgres psql -U postgres -c "CREATE DATABASE bike_demand_db;"
   ```

2. **Recreate containers**
   ```bash
   cd infrastructure
   docker compose down -v  # Remove volumes
   docker compose up -d
   ```

3. **Check docker-compose.yml**
   ```yaml
   environment:
     POSTGRES_DB: bike_demand_db  # Must match .env
   ```

---

### Issue: "Table does not exist"

**Symptoms:**
```sql
ERROR: relation "bike_stations" does not exist
```

**Solutions:**

1. **Run schema.sql**
   ```bash
   cd infrastructure
   docker compose exec -T postgres psql -U postgres -d bike_demand_db < postgres/schema.sql
   ```

2. **Verify tables exist**
   ```bash
   docker compose exec postgres psql -U postgres -d bike_demand_db -c "\dt"
   ```

3. **Check for errors in schema.sql**
   ```bash
   # Look for SQL syntax errors
   cat postgres/schema.sql
   ```

---

### Issue: "Slow query performance"

**Symptoms:**
- Queries taking >1 second
- Dashboard loading slowly

**Solutions:**

1. **Check missing indexes**
   ```sql
   -- List indexes
   \di

   -- Create missing indexes
   CREATE INDEX idx_bike_station_status_station_timestamp
   ON bike_station_status (station_id, timestamp DESC);
   ```

2. **Analyze query performance**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM bike_station_status
   WHERE station_id = '123'
   AND timestamp > NOW() - INTERVAL '24 hours';
   ```

3. **Vacuum database**
   ```bash
   docker compose exec postgres psql -U postgres -d bike_demand_db -c "VACUUM ANALYZE;"
   ```

---

## API Issues

### Issue: "API returns 503 Service Unavailable"

**Symptoms:**
- `/health` endpoint returns 503
- Dashboard shows "API Offline"

**Solutions:**

1. **Check if API container is running**
   ```bash
   docker compose ps api
   # Should show "Up"
   ```

2. **Check API logs**
   ```bash
   docker compose logs api --tail=50
   # Look for errors
   ```

3. **Verify API URL in dashboard**
   ```python
   # dashboard/app.py
   API_URL = os.getenv("API_URL", "http://bike_demand_api:8000")
   # Must use container name when running in Docker
   ```

4. **Test API directly**
   ```bash
   # From host machine
   curl http://localhost:8000/health

   # From inside Docker network
   docker compose exec dashboard curl http://bike_demand_api:8000/health
   ```

---

### Issue: "No model loaded" error

**Symptoms:**
```json
{
  "detail": "No production model found in MLflow"
}
```

**Solutions:**

1. **Check MLflow registry**
   - Open http://localhost:5000
   - Go to "Models" tab
   - Verify model exists with "Production" stage

2. **Promote model to Production**
   ```python
   import mlflow
   mlflow.set_tracking_uri("http://localhost:5000")

   client = mlflow.tracking.MlflowClient()
   client.transition_model_version_stage(
       name="bike-demand-forecaster",
       version=1,
       stage="Production"
   )
   ```

3. **Train a model first**
   ```bash
   # Run training pipeline
   docker build -t bike-demand-trainer -f docker/training/Dockerfile .
   docker run --rm --network infrastructure_bike_demand_network \
     -e MLFLOW_TRACKING_URI=http://bike_demand_mlflow:5000 \
     bike-demand-trainer:latest
   ```

---

### Issue: "Prediction returns NaN or very wrong values"

**Symptoms:**
- API returns `predicted_demand: NaN`
- Or predictions like `predicted_demand: 99999`

**Solutions:**

1. **Check for missing features**
   ```bash
   # API logs should show which features are missing
   docker compose logs api | grep "Missing features"
   ```

2. **Verify feature generation**
   ```python
   # Test feature generation
   from src.serving.predictor import BikeDedemandPredictor
   predictor = BikeDedemandPredictor()
   result = predictor.predict(station_id="test-station-1")
   print(result)
   ```

3. **Check model input range**
   ```python
   # Features might be out of expected range
   # Example: hour_of_day should be 0-23, not 24
   ```

---

## Dashboard Issues

### Issue: "Dashboard shows blank page"

**Symptoms:**
- Streamlit loads but shows nothing
- Spinners forever

**Solutions:**

1. **Check browser console for errors**
   - Open DevTools (F12)
   - Look for JavaScript errors

2. **Check Streamlit logs**
   ```bash
   docker compose logs dashboard --tail=100
   ```

3. **Verify database connection**
   ```bash
   # Dashboard must be on same Docker network
   docker compose exec dashboard ping bike_demand_postgres
   ```

4. **Clear Streamlit cache**
   - Click "☰" → "Clear cache" in dashboard
   - Or restart dashboard container

---

### Issue: "No stations showing in dropdown"

**Symptoms:**
- Station selector is empty
- Error: "No stations found"

**Solutions:**

1. **Verify stations exist in database**
   ```bash
   docker compose exec postgres psql -U postgres -d bike_demand_db \
     -c "SELECT COUNT(*) FROM bike_stations WHERE is_active = TRUE;"
   ```

2. **Load station data**
   ```bash
   # Run backfill script
   docker compose run --rm api python scripts/backfill_historical_data.py
   ```

3. **Check SQL query in dashboard**
   ```python
   # dashboard/pages/1_demand_forecast.py
   # Verify query executes without errors
   ```

---

## Airflow Issues

### Issue: "Airflow webserver won't start"

**Symptoms:**
```
Error: "AirflowException: Already running PID: 1"
```

**Solutions:**

1. **Reset Airflow database**
   ```bash
   docker compose down
   docker volume rm infrastructure_airflow_data
   docker compose up -d airflow-init
   docker compose up -d
   ```

2. **Check Airflow logs**
   ```bash
   docker compose logs airflow-webserver
   docker compose logs airflow-scheduler
   ```

3. **Increase memory for Docker**
   - Docker Desktop → Settings → Resources
   - Set to 8GB+ RAM

---

### Issue: "DAGs not appearing in UI"

**Symptoms:**
- Airflow UI shows no DAGs
- Or DAGs are "paused"

**Solutions:**

1. **Verify DAG files exist**
   ```bash
   ls airflow/dags/
   # Should show .py files
   ```

2. **Check DAG syntax errors**
   ```bash
   docker compose exec airflow-scheduler airflow dags list
   # Look for import errors
   ```

3. **Enable DAG**
   - In Airflow UI, click toggle to "unpause" DAG

4. **Trigger DAG manually**
   - Click "▶" button to run DAG

---

### Issue: "DAG tasks failing"

**Symptoms:**
- Tasks show red (failed)
- Error: "Task failed with exit code 1"

**Solutions:**

1. **View task logs**
   - Click on failed task
   - Click "Log" tab
   - Read error message

2. **Common failures:**

   **Import errors:**
   ```python
   # Fix: Install missing dependency in Dockerfile
   RUN pip install missing-package
   ```

   **Connection refused:**
   ```python
   # Fix: Use container names, not localhost
   DB_HOST=bike_demand_postgres  # not localhost
   ```

   **File not found:**
   ```python
   # Fix: Mount volume in docker-compose.yml
   volumes:
     - ../src:/opt/airflow/src
   ```

---

## Model Training Issues

### Issue: "No data retrieved from feature store"

**Symptoms:**
```
ValueError: No data retrieved from feature store
```

**Solutions:**

1. **Generate features first**
   ```bash
   docker compose run --rm api python scripts/generate_features.py
   ```

2. **Verify features exist**
   ```bash
   docker compose exec postgres psql -U postgres -d bike_demand_db \
     -c "SELECT COUNT(*) FROM features WHERE feature_version = 'v1.0';"
   # Should return > 0
   ```

3. **Check timestamp range**
   ```sql
   -- Features must cover the date range you're querying
   SELECT MIN(timestamp), MAX(timestamp) FROM features;
   ```

---

### Issue: "Training runs but RMSE is very high"

**Symptoms:**
- RMSE > 5.0 bikes
- Model performs poorly

**Solutions:**

1. **Check for data quality issues**
   ```python
   # Look for NaN, infinite values
   import pandas as pd
   df = pd.read_sql("SELECT * FROM features LIMIT 1000", conn)
   print(df.isnull().sum())  # NaN count per column
   print(df.describe())      # Check for outliers
   ```

2. **Verify feature engineering**
   ```python
   # Are lag features correct?
   # Example: bikes_lag_1h should be bikes_available from 1 hour ago
   ```

3. **Increase model complexity**
   ```yaml
   # config/model_config.yml
   lightgbm:
     n_estimators: 200  # Increase from 100
     max_depth: 8       # Increase from 6
   ```

4. **Check for data leakage**
   ```python
   # Make sure train/test split is chronological
   # Don't shuffle time-series data!
   ```

---

### Issue: "MLflow experiment tracking not working"

**Symptoms:**
- No experiments in MLflow UI
- Logs say "Experiment '1' does not exist"

**Solutions:**

1. **Create experiment**
   ```python
   import mlflow
   mlflow.create_experiment("bike-demand-forecasting")
   ```

2. **Verify MLflow connection**
   ```bash
   curl http://localhost:5000/api/2.0/mlflow/experiments/list
   # Should return JSON with experiments
   ```

3. **Check MLFLOW_TRACKING_URI**
   ```bash
   # In training container
   echo $MLFLOW_TRACKING_URI
   # Should be: http://bike_demand_mlflow:5000
   ```

---

## Performance Issues

### Issue: "API latency > 500ms"

**Symptoms:**
- Predictions take too long
- Dashboard is slow

**Solutions:**

1. **Profile prediction code**
   ```python
   import time
   start = time.time()
   result = predictor.predict(station_id="123")
   print(f"Prediction took {time.time() - start:.2f}s")
   ```

2. **Cache features in memory**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def get_features(station_id, timestamp):
       # Cached for repeated calls
       return features
   ```

3. **Use async endpoints**
   ```python
   @app.get("/predict")
   async def predict():
       # Use asyncio for concurrent requests
       pass
   ```

4. **Add indexes to database**
   ```sql
   CREATE INDEX idx_features_lookup
   ON features (station_id, timestamp DESC, feature_version);
   ```

---

### Issue: "High memory usage"

**Symptoms:**
- Docker uses >8GB RAM
- System becomes slow

**Solutions:**

1. **Check container memory**
   ```bash
   docker stats
   # Shows per-container memory usage
   ```

2. **Limit container memory**
   ```yaml
   services:
     api:
       deploy:
         resources:
           limits:
             memory: 1G
   ```

3. **Reduce feature store cache**
   ```python
   # src/utils/feature_store.py
   @lru_cache(maxsize=100)  # Reduce from 1000
   ```

---

## Data Quality Issues

### Issue: "Missing data for recent hours"

**Symptoms:**
- Features missing for last N hours
- Predictions fail for current time

**Solutions:**

1. **Run data collection manually**
   ```bash
   docker compose run --rm api python scripts/backfill_historical_data.py
   ```

2. **Check Airflow DAG schedule**
   ```python
   # airflow/dags/data_ingestion_dag.py
   schedule_interval="*/15 * * * *"  # Every 15 minutes
   ```

3. **Verify API credentials**
   ```bash
   # Check if weather API key is valid
   curl "https://api.openweathermap.org/data/2.5/weather?q=NewYork&appid=YOUR_KEY"
   ```

---

### Issue: "Data drift detected"

**Symptoms:**
- Monitoring alerts show drift
- Model performance degrading

**Solutions:**

1. **Investigate drift source**
   ```python
   # Check which features are drifting
   from src.monitoring.data_drift_detector import DataDriftDetector
   detector = DataDriftDetector()
   report = detector.detect_drift()
   print(report)
   ```

2. **Retrain model**
   ```bash
   # Trigger training DAG in Airflow
   docker compose exec airflow-scheduler airflow dags trigger model_training_dag
   ```

3. **Update feature engineering**
   ```python
   # Add new features to capture changing patterns
   ```

---

## Getting More Help

If you're still stuck:

1. **Check logs systematically:**
   ```bash
   docker compose logs postgres
   docker compose logs mlflow
   docker compose logs api
   docker compose logs dashboard
   docker compose logs airflow-scheduler
   ```

2. **Search GitHub Issues:**
   - [Project Issues](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)

3. **Ask in GitHub Discussions:**
   - [Start a discussion](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/discussions)

4. **Report a bug:**
   - Include error messages
   - Include relevant logs
   - Describe steps to reproduce

---

## Debugging Checklist

When something doesn't work:

- [ ] Check if all containers are running (`docker compose ps`)
- [ ] Check logs for error messages
- [ ] Verify environment variables in `.env`
- [ ] Confirm database schema is created
- [ ] Test database connection
- [ ] Verify data exists in tables
- [ ] Check Docker network connectivity
- [ ] Restart containers (`docker compose restart`)
- [ ] As last resort, rebuild (`docker compose down -v && docker compose up -d`)

---

**Still having issues?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues) with:
- Error message
- What you tried
- Relevant logs
- Your environment (OS, Docker version)
