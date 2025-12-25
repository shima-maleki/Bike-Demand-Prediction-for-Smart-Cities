# Production Workflow - How It Works End-to-End

## 🏗️ Production Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION SYSTEM                             │
└─────────────────────────────────────────────────────────────────────┘

📡 External APIs                   🔄 Airflow Orchestration
├── Citi Bike GBFS API             ├── Data Ingestion DAG (every 15 min)
└── OpenWeatherMap API             ├── Weather Enrichment DAG (every 30 min)
                                   ├── Feature Engineering DAG (every 1 hour)
                                   └── Model Training DAG (daily at 2 AM)
          │                                    │
          ▼                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐                │
│  │ bike_stations│  │ weather_data │  │  features   │                │
│  │ station_status│  │              │  │  (JSONB)    │                │
│  └──────────────┘  └──────────────┘  └─────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Feature Engineering                              │
│  Temporal • Lag • Rolling • Weather • Holiday Features                │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Model Training (Automated)                       │
│  XGBoost • LightGBM • CatBoost → MLflow Tracking & Registry          │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Model Registry (MLflow)                          │
│  Production Model • Staging • Archived                                │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Server (24/7)                            │
│  Loads production model on startup → Serves predictions               │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Streamlit Dashboard (24/7)                       │
│  Visualizations • Monitoring • Predictions                            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⏰ Automated Schedule (No Manual Intervention)

### **Every 15 Minutes** 🕐
**DAG: `data_ingestion`**
```python
# airflow/dags/data_ingestion_dag.py
@dag(schedule_interval="*/15 * * * *")  # Every 15 minutes
def data_ingestion():
    # 1. Call Citi Bike API
    # 2. Get all station statuses
    # 3. Insert into PostgreSQL (bike_station_status table)
    # 4. Log metrics
```

### **Every 30 Minutes** 🕑
**DAG: `weather_enrichment`**
```python
# airflow/dags/weather_enrichment_dag.py
@dag(schedule_interval="*/30 * * * *")  # Every 30 minutes
def weather_enrichment():
    # 1. Call OpenWeatherMap API
    # 2. Get current weather for NYC
    # 3. Insert into PostgreSQL (weather_data table)
    # 4. Log metrics
```

### **Every Hour** 🕐🕑🕒
**DAG: `feature_engineering`**
```python
# airflow/dags/feature_engineering_dag.py
@dag(schedule_interval="0 * * * *")  # Every hour
def feature_engineering():
    # 1. Read bike_station_status + weather_data from DB
    # 2. Generate temporal features (hour, day, season)
    # 3. Calculate lag features (1h, 24h, 168h)
    # 4. Compute rolling statistics (3h, 24h windows)
    # 5. Enrich with weather features
    # 6. Add holiday indicators
    # 7. Store in features table (JSONB column)
```

### **Daily at 2 AM** 🌙
**DAG: `model_training`**
```python
# airflow/dags/model_training_dag.py
@dag(schedule_interval="0 2 * * *")  # Daily at 2 AM
def model_training():
    # 1. Read last 30 days of features from DB
    # 2. Prepare training data (70/15/15 split)
    # 3. Train XGBoost, LightGBM, CatBoost
    # 4. Evaluate models (RMSE, MAE, R², MAPE)
    # 5. Log to MLflow
    # 6. Compare with current production model
    # 7. IF new model is better:
    #    - Promote to "Production" stage
    #    - Archive old model
    #    - Send alert to Slack
```

---

## 🔄 Day-to-Day Operation

### **Morning (8 AM)**
```
User opens dashboard → http://localhost:8501

Dashboard shows:
✅ Data freshness: Last updated 7:45 AM (15 min ago)
✅ Model status: XGBoost v12 (trained last night at 2 AM)
✅ Predictions: Next 24 hours forecast
✅ Accuracy: Test RMSE: 3.2 bikes
```

### **Throughout the Day**
```
9:00 AM  → Data collected (bike statuses)
9:15 AM  → Data collected (bike statuses)
9:30 AM  → Data collected (bike statuses) + Weather updated
9:45 AM  → Data collected (bike statuses)
10:00 AM → Data collected + Features generated for 9 AM
...continues every 15 min
```

### **Next Night (2 AM)**
```
2:00 AM → Airflow triggers model training
2:05 AM → Training starts with last 30 days of data
2:15 AM → Models trained, evaluated
2:16 AM → New model is 5% better than current
2:17 AM → Promoted to Production in MLflow
2:18 AM → Slack notification: "🎉 New model deployed! RMSE improved from 3.2 → 3.0"
```

### **API Automatically Updates**
```
2:20 AM → API detects new production model
2:20 AM → API reloads model (no downtime)
2:21 AM → New predictions use updated model
```

---

## 📁 Production File Structure

```
/opt/bike-demand-prediction/          # Production server path
├── airflow/
│   ├── dags/
│   │   ├── data_ingestion_dag.py      # Runs every 15 min
│   │   ├── weather_enrichment_dag.py  # Runs every 30 min
│   │   ├── feature_engineering_dag.py # Runs every hour
│   │   └── model_training_dag.py      # Runs daily at 2 AM
│   └── logs/                          # Airflow execution logs
│
├── src/
│   ├── data/
│   │   ├── collectors/                # API collectors
│   │   ├── processors/                # Data validation
│   │   └── storage/                   # PostgreSQL handlers
│   ├── features/                      # Feature engineering
│   ├── training/                      # Training pipeline
│   └── serving/
│       └── api/                       # FastAPI (runs 24/7)
│
├── mlruns/                            # MLflow tracking
├── models/                            # Archived model files
└── logs/                              # Application logs
```

---

## 🚀 Production Deployment Steps

### **1. Initial Setup (One Time)**

```bash
# Clone repository
git clone https://github.com/your-org/bike-demand-prediction.git
cd bike-demand-prediction

# Install dependencies
pip install -e .

# Start infrastructure
docker-compose -f infrastructure/docker-compose.yml up -d

# Wait for services
sleep 30

# Initialize database
psql $DATABASE_URL -f infrastructure/postgres/schema.sql

# Verify
docker-compose -f infrastructure/docker-compose.yml ps
```

### **2. Start Airflow (Orchestration)**

```bash
# Initialize Airflow
docker-compose -f infrastructure/docker-compose.yml up -d airflow-init

# Start scheduler and webserver
docker-compose -f infrastructure/docker-compose.yml up -d airflow-webserver airflow-scheduler

# Access UI
open http://localhost:8080
# User: airflow, Password: airflow

# Enable DAGs
airflow dags unpause data_ingestion
airflow dags unpause weather_enrichment
airflow dags unpause feature_engineering
airflow dags unpause model_training
```

### **3. Initial Data Collection (Bootstrap)**

```bash
# Collect first batch manually
python scripts/bootstrap_data.py

# This collects:
# - All bike stations
# - Current statuses
# - Initial weather data
# - Backfills last 7 days if possible
```

### **4. Start API Server (Production Mode)**

```bash
# Option A: Direct
uvicorn src.serving.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Option B: Docker
docker-compose -f infrastructure/docker-compose.yml up -d api

# Verify
curl http://localhost:8000/health
```

### **5. Start Dashboard**

```bash
# Configure secrets
cp dashboard/.streamlit/secrets.toml.example dashboard/.streamlit/secrets.toml
nano dashboard/.streamlit/secrets.toml  # Set API_URL

# Start
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0

# Or Docker
docker-compose -f infrastructure/docker-compose.yml up -d dashboard
```

### **6. Monitor Everything**

```bash
# View Airflow DAGs
open http://localhost:8080

# View MLflow experiments
open http://localhost:5000

# View API docs
open http://localhost:8000/docs

# View Dashboard
open http://localhost:8501
```

---

## 🔍 What Happens When New Data Arrives

### **Scenario: 3:15 PM, Thursday**

```
1. Airflow Scheduler: "Time to run data_ingestion DAG"
   ├─→ Task 1: Call Citi Bike API
   ├─→ Task 2: Validate data (Great Expectations)
   ├─→ Task 3: Insert 1,700 station statuses into PostgreSQL
   └─→ Task 4: Log success to monitoring

2. Database now has: 1,700 new rows in bike_station_status

3. At 4:00 PM, Airflow Scheduler: "Time to run feature_engineering DAG"
   ├─→ Task 1: Read last hour of bike_station_status
   ├─→ Task 2: Join with weather_data
   ├─→ Task 3: Calculate temporal features (hour=15, day=Thursday, etc.)
   ├─→ Task 4: Calculate lag features (demand 1h ago, 24h ago)
   ├─→ Task 5: Calculate rolling stats (mean last 3h, max last 24h)
   ├─→ Task 6: Store 100+ features in features table
   └─→ Task 7: Log feature statistics

4. Database now has: Feature vectors for 3 PM data

5. API Server (running 24/7):
   ├─→ User requests: GET /predict/station/station_1/forecast?hours_ahead=24
   ├─→ API reads current features from database
   ├─→ API generates future features (weather forecasts if available)
   ├─→ Model predicts demand for next 24 hours
   └─→ Returns JSON response in <100ms

6. Dashboard (running 24/7):
   ├─→ Refreshes every 30 seconds
   ├─→ Shows: "Last data: 3:15 PM (2 min ago)"
   └─→ Displays real-time predictions
```

---

## 🎯 Model Retraining Flow

### **Every Night at 2 AM**

```python
# airflow/dags/model_training_dag.py

from src.training.train_pipeline import train_model
from src.serving.model_loader import promote_model_to_production

def training_task():
    # 1. Train new model
    results = train_model(
        model_type="xgboost",
        days_back=30,  # Use last 30 days
    )

    # 2. Get current production model metrics
    current_model = get_production_model()
    current_rmse = current_model.metrics['test_rmse']

    new_rmse = results['metrics']['test_rmse']

    # 3. Compare
    if new_rmse < current_rmse * 0.95:  # 5% improvement
        # Promote new model
        promote_model_to_production(results['run_id'])

        # Send alert
        send_slack_notification(
            f"🎉 New model deployed!\n"
            f"Old RMSE: {current_rmse:.2f}\n"
            f"New RMSE: {new_rmse:.2f}\n"
            f"Improvement: {(1 - new_rmse/current_rmse)*100:.1f}%"
        )
    else:
        # Keep current model
        send_slack_notification(
            f"ℹ️ New model trained but not better than current.\n"
            f"Current RMSE: {current_rmse:.2f}\n"
            f"New RMSE: {new_rmse:.2f}"
        )
```

### **API Detects Model Update**

```python
# src/serving/api/main.py

@app.on_event("startup")
async def startup_event():
    # Load production model
    model_loader.load_production_model()

    # Start background task to check for updates
    asyncio.create_task(check_model_updates())

async def check_model_updates():
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes

        current_version = model_loader.current_version
        latest_version = get_latest_production_version()

        if latest_version > current_version:
            logger.info(f"New model detected: v{latest_version}")
            model_loader.reload_model()
            logger.info("Model reloaded successfully")
```

---

## 📊 Monitoring & Alerts

### **Prometheus Metrics**

```python
# src/serving/api/main.py

from prometheus_client import Counter, Histogram, Gauge

prediction_counter = Counter('predictions_total', 'Total predictions made')
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
model_version_gauge = Gauge('model_version', 'Current model version')

@app.post("/predict")
async def predict(request: PredictionRequest):
    with prediction_latency.time():
        result = predictor.predict(request)
        prediction_counter.inc()
        return result
```

### **Grafana Dashboards**

```yaml
# infrastructure/monitoring/grafana/dashboards/model_monitoring.json

Panels:
  - Predictions per minute (last 24h)
  - API latency (p50, p95, p99)
  - Model version over time
  - Prediction errors (RMSE, MAE)
  - Data freshness (time since last data)
  - DAG success rate
```

---

## 🔐 Production Checklist

Before going live:

- [ ] PostgreSQL replicated (master-slave)
- [ ] MLflow backend on S3/Azure Blob
- [ ] Airflow with CeleryExecutor (for scaling)
- [ ] API with load balancer (multiple instances)
- [ ] HTTPS with SSL certificates
- [ ] Authentication (API keys, OAuth)
- [ ] Rate limiting (10 requests/min for free tier)
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Alerting (Slack, PagerDuty)
- [ ] Backups (daily database dumps)
- [ ] Logging (centralized with ELK stack)
- [ ] CI/CD (GitHub Actions)
- [ ] Documentation (API docs, runbooks)

---

## 🚨 Disaster Recovery

### **API Down**
```bash
# Auto-restart with Docker
restart: always

# Health check
docker-compose -f infrastructure/docker-compose.yml ps
docker-compose -f infrastructure/docker-compose.yml restart api
```

### **Database Corruption**
```bash
# Restore from backup
pg_restore -d bike_demand_db backup_2025_01_15.dump
```

### **Model Regression**
```bash
# Rollback to previous version
python scripts/rollback_model.py --version 11

# Or via MLflow UI
# MLflow UI → Models → bike-demand-forecasting → v11 → Transition to Production
```

---

## 📈 Scaling for Growth

### **10K requests/day → 1M requests/day**

```yaml
# infrastructure/docker-compose.prod.yml

api:
  replicas: 10
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G

nginx:  # Load balancer
  image: nginx:latest
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
  ports:
    - "80:80"
```

### **Horizontal Scaling**
- API: 10+ instances behind load balancer
- Database: Read replicas for queries
- Airflow: CeleryExecutor with 5+ workers
- MLflow: S3 for artifact storage

---

## 🎓 Key Takeaways

1. **Fully Automated**: No manual intervention after setup
2. **Self-Healing**: Models retrain automatically when performance degrades
3. **Always Fresh**: Data collected every 15 min, features every hour
4. **Zero Downtime**: Rolling deployments, model hot-swapping
5. **Observable**: Full monitoring, logging, alerting
6. **Scalable**: Can handle 1M+ predictions/day

This is **Level 2 MLOps** - Training automation + production monitoring! 🚀
