# 🚀 Start Production System - Quick Guide

This guide shows you how to start the **complete automated production system** in 10 minutes.

---

## 📋 Prerequisites

- ✅ Docker & Docker Compose installed
- ✅ Python 3.11+ with dependencies installed
- ✅ PostgreSQL accessible (via Docker)
- ✅ Ports available: 5000 (MLflow), 5432 (PostgreSQL), 8000 (API), 8080 (Airflow), 8501 (Dashboard)

---

## 🎯 Quick Start (10 Minutes)

### **Step 1: Start Infrastructure Services (2 min)**

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

### **Step 2: Start Airflow (3 min)**

```bash
# Initialize Airflow (first time only)
docker-compose -f infrastructure/docker-compose.yml up -d airflow-init

# Wait for initialization
sleep 45

# Start Airflow webserver and scheduler
docker-compose -f infrastructure/docker-compose.yml up -d airflow-webserver airflow-scheduler

# Verify
docker-compose -f infrastructure/docker-compose.yml logs -f airflow-webserver | grep "Listening at"
```

**Access Airflow UI:**
- URL: http://localhost:8080
- Username: `airflow`
- Password: `airflow`

---

### **Step 3: Enable DAGs (1 min)**

In Airflow UI (http://localhost:8080):

1. **Toggle ON these 4 DAGs:**
   - ✅ `data_ingestion` (runs every 15 min)
   - ✅ `weather_enrichment` (runs every 30 min)
   - ✅ `feature_engineering` (runs every 1 hour)
   - ✅ `model_training` (runs daily at 2 AM)

2. **Trigger manually for first run:**
   - Click on `data_ingestion` → Click "Trigger DAG" (▶️)
   - Wait 2-3 minutes
   - Click on `weather_enrichment` → Trigger
   - Wait 2-3 minutes
   - Click on `feature_engineering` → Trigger

**Or via CLI:**
```bash
# Trigger DAGs manually
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger data_ingestion

docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger weather_enrichment
```

---

### **Step 4: Initial Model Training (2 min)**

**Option A: Use the notebook (RECOMMENDED for first time)**
```bash
jupyter notebook notebooks/00_end_to_end_system_demo.ipynb
# Run all cells to train models with synthetic data
```

**Option B: Use training script** (requires real data from Step 3)
```bash
python train_model.py
```

**Option C: Trigger Airflow DAG**
```bash
# After DAGs have run and collected data
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger model_training
```

---

### **Step 5: Start API Server (1 min)**

```bash
# Start in background
uvicorn src.serving.api.main:app --host 0.0.0.0 --port 8000 &

# Verify
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model_status": "loaded",
  "database_status": "connected"
}
```

**API Documentation:** http://localhost:8000/docs

---

### **Step 6: Start Dashboard (1 min)**

```bash
# Start in background
streamlit run dashboard/app.py --server.port 8501 &

# Or use Docker
docker-compose -f infrastructure/docker-compose.yml up -d dashboard
```

**Access Dashboard:** http://localhost:8501

---

## ✅ Verification Checklist

### **Check All Services:**

```bash
# PostgreSQL
docker-compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d bike_demand_db -c "SELECT COUNT(*) FROM bike_stations;"

# MLflow
curl http://localhost:5000/health

# Airflow
curl http://localhost:8080/health

# API
curl http://localhost:8000/health/detailed

# Dashboard
curl -I http://localhost:8501
```

### **Check DAG Status:**

In Airflow UI (http://localhost:8080):
- All 4 DAGs should show green checkmarks ✅
- Recent runs should be "success"

### **Check MLflow:**

Open http://localhost:5000
- Should see experiments: "bike-demand-forecasting"
- Should see at least 1 model run

---

## 🔄 What Happens Now (Automated)

### **Every 15 Minutes:**
```
09:00 → Data ingestion DAG runs
        ├─ Collect bike station statuses
        ├─ Insert into PostgreSQL
        └─ Log metrics

09:15 → Data ingestion DAG runs again
        └─ Continuous data collection...
```

### **Every 30 Minutes:**
```
09:00 → Weather enrichment DAG runs
        ├─ Fetch NYC weather
        ├─ Insert into PostgreSQL
        └─ Log metrics

09:30 → Weather enrichment DAG runs again
```

### **Every Hour:**
```
10:00 → Feature engineering DAG runs
        ├─ Read bike_station_status + weather_data
        ├─ Generate 100+ features
        ├─ Store in features table
        └─ Log feature statistics
```

### **Daily at 2 AM:**
```
02:00 → Model training DAG runs
        ├─ Load last 30 days of features
        ├─ Train XGBoost, LightGBM, CatBoost
        ├─ Evaluate models
        ├─ Log to MLflow
        ├─ Compare with production model
        └─ Promote if better (automatic!)
```

---

## 📊 Monitoring Your System

### **Airflow UI** (http://localhost:8080)
- View DAG runs
- Check task logs
- Monitor execution time
- See failures and retries

### **MLflow UI** (http://localhost:5000)
- View all experiments
- Compare model metrics
- See model versions
- Track artifacts

### **Dashboard** (http://localhost:8501)
- Real-time predictions
- System health status
- Model performance
- Data quality

### **API Docs** (http://localhost:8000/docs)
- Test predictions
- View API schema
- Try different endpoints

---

## 🛠️ Common Tasks

### **View Logs:**
```bash
# Airflow logs
docker-compose -f infrastructure/docker-compose.yml logs -f airflow-scheduler

# API logs
tail -f logs/api.log

# Database logs
docker-compose -f infrastructure/docker-compose.yml logs -f postgres
```

### **Restart a Service:**
```bash
# Restart API
pkill -f uvicorn
uvicorn src.serving.api.main:app --host 0.0.0.0 --port 8000 &

# Restart Airflow
docker-compose -f infrastructure/docker-compose.yml restart airflow-scheduler
```

### **Check Data:**
```bash
# How much data collected?
psql postgresql://postgres:postgres@localhost:5432/bike_demand_db

# In psql:
SELECT COUNT(*) FROM bike_station_status;
SELECT COUNT(*) FROM weather_data;
SELECT COUNT(*) FROM features;

# Latest data
SELECT * FROM bike_station_status ORDER BY timestamp DESC LIMIT 10;
```

### **Manually Trigger Training:**
```bash
# Via Airflow UI
# http://localhost:8080 → model_training → Trigger DAG

# Or via CLI
docker-compose -f infrastructure/docker-compose.yml exec airflow-scheduler \
  airflow dags trigger model_training
```

---

## 🚨 Troubleshooting

### **DAG Not Running?**
```bash
# Check scheduler is running
docker-compose -f infrastructure/docker-compose.yml ps airflow-scheduler

# Check DAG is enabled
# Airflow UI → DAGs → Toggle switch should be ON

# View DAG errors
docker-compose -f infrastructure/docker-compose.yml logs airflow-scheduler | grep ERROR
```

### **No Data in Database?**
```bash
# Check if DAG succeeded
# Airflow UI → data_ingestion → View last run

# Manually run data collection
python -c "from src.data.collectors.citi_bike_collector import CitiBikeCollector; \
           c = CitiBikeCollector(); \
           with c: print(len(c.collect_station_status()['data']['stations']))"
```

### **API Shows "No Model"?**
```bash
# Check MLflow has models
curl http://localhost:5000/api/2.0/mlflow/registered-models/search

# Train a model manually
python train_model.py

# Or run the notebook
jupyter notebook notebooks/00_end_to_end_system_demo.ipynb
```

---

## 🎯 Success Criteria

You're ready for production when:

- ✅ All 4 DAGs enabled and running successfully
- ✅ Data being collected every 15 minutes
- ✅ Features generated every hour
- ✅ At least 1 model trained and in MLflow
- ✅ API returning predictions successfully
- ✅ Dashboard showing real-time data

---

## 📈 Next Steps

1. **Monitor for 24 hours** - Ensure DAGs run successfully
2. **After 7 days** - Enough data for good model training
3. **After 30 days** - Production-quality models
4. **Set up alerts** - Slack/email for DAG failures
5. **Add monitoring** - Prometheus + Grafana
6. **Scale up** - Add more workers if needed

---

## 🆘 Getting Help

- **View full workflow:** See [docs/PRODUCTION_WORKFLOW.md](docs/PRODUCTION_WORKFLOW.md)
- **API issues:** Check [docs/API_QUICK_START.md](docs/API_QUICK_START.md)
- **Dashboard issues:** See [dashboard/README.md](dashboard/README.md)
- **Airflow docs:** https://airflow.apache.org/docs/

---

## 🎉 You're Now Running a Level 2 MLOps System!

Your system is now:
- 🤖 **Fully Automated** - No manual intervention
- 🔄 **Self-Training** - Models retrain nightly
- 📊 **Observable** - Full monitoring & logging
- 🚀 **Production-Ready** - Can handle real traffic

**Congratulations!** 🎊
