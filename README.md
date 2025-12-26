# Bike Demand Prediction for Smart Cities

**Level 2 MLOps** production-grade bike demand forecasting system with automated data pipelines, experiment tracking, model registry, and comprehensive monitoring.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## Overview

Production-ready machine learning system that predicts bike rental demand using real-world public APIs and historical data. Built with **Docker-first architecture** for seamless deployment, the system processes NYC Citi Bike trip data, enriches it with weather signals, engineers 22+ time-series features, and trains ensemble models (XGBoost + LightGBM) achieving **RMSE 0.61 bikes**.

### Key Features

- ✅ **100% Docker-Based**: All services containerized for production deployment
- 📊 **Real Data**: 50K+ historical bike station records + weather data
- 🤖 **Automated ML Pipeline**: Feature engineering → Training → Model registry
- 📈 **Experiment Tracking**: MLflow with model versioning and metrics
- 🔄 **Airflow Orchestration**: 4 DAGs for data/training automation
- 🎯 **Production Models**: XGBoost (RMSE 0.63) & LightGBM (RMSE 0.61)
- 📊 **Interactive Dashboard**: Streamlit UI for forecasts and monitoring
- 🔍 **Comprehensive Monitoring**: Prometheus + Grafana + Evidently AI
- 🚀 **CI/CD Ready**: GitHub Actions for automated testing and deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Production Infrastructure                      │
│                     (Docker Compose)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│  PostgreSQL  │    │   MLflow     │      │   Airflow    │
│   Database   │    │   Server     │      │  Scheduler   │
│              │    │              │      │              │
│ • Stations   │    │ • Experiments│      │ • 4 DAGs     │
│ • Status     │    │ • Models     │      │ • Automation │
│ • Weather    │    │ • Registry   │      │              │
│ • Features   │    └──────────────┘      └──────────────┘
└──────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│              Training Pipeline (Docker Container)            │
│                                                              │
│  1. Load Features → 2. Train XGBoost/LightGBM              │
│  3. Evaluate Models → 4. Register to MLflow                │
│  5. Promote Best Model to Production                       │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                   Serving & Visualization                    │
│                                                              │
│  ┌────────────┐         ┌─────────────┐                    │
│  │  FastAPI   │         │  Streamlit  │                    │
│  │   Server   │         │  Dashboard  │                    │
│  └────────────┘         └─────────────┘                    │
│                                                              │
│  ┌────────────┐         ┌─────────────┐                    │
│  │ Prometheus │         │   Grafana   │                    │
│  │  Metrics   │         │ Dashboards  │                    │
│  └────────────┘         └─────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Orchestration** | Apache Airflow 2.8.0 |
| **Database** | PostgreSQL 16 (Alpine) |
| **ML Models** | XGBoost 2.0+, LightGBM 4.1+, CatBoost 1.2+ |
| **Experiment Tracking** | MLflow 2.9+ |
| **API Framework** | FastAPI 0.108+ |
| **Dashboard** | Streamlit 1.29+ |
| **Monitoring** | Prometheus, Grafana, Evidently AI |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |

## Quick Start (10 Minutes)

### Prerequisites

- **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop/))
- **Git**
- **OpenWeatherMap API Key** ([Free signup](https://openweathermap.org/api))
- 8GB+ RAM (for Docker containers)

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/Bike-Demand-Prediction-for-Smart-Cities.git
cd Bike-Demand-Prediction-for-Smart-Cities
```

### Step 2: Configure Environment

```bash
# Create environment file
cp .env.example .env

# Edit .env and add your API key
# WEATHER_API_KEY=your_api_key_here
```

### Step 3: Start Production Infrastructure

```bash
cd infrastructure
docker-compose up -d
```

This starts all services:
- **PostgreSQL** (port 5432)
- **MLflow** (port 5000)
- **Airflow Webserver** (port 8080)
- **Airflow Scheduler**
- **Prometheus** (port 9090)
- **Grafana** (port 3000)

**Wait 2 minutes** for all services to become healthy.

### Step 4: Verify Services

```bash
# Check all containers are running
docker ps

# You should see:
# - bike_demand_postgres (healthy)
# - bike_demand_mlflow (healthy)
# - bike_demand_airflow_webserver (healthy)
# - bike_demand_airflow_scheduler (running)
# - bike_demand_prometheus (running)
# - bike_demand_grafana (running)
```

### Step 5: Access Web Interfaces

Open in your browser:

- **MLflow UI**: http://localhost:5000
- **Airflow UI**: http://localhost:8080
  - Username: `admin`
  - Password: `admin`
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

### Step 6: Load Historical Data

The system includes production scripts for data backfill:

```bash
# 1. Backfill historical bike data (Nov 2025, 50K records)
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -v $(pwd)/scripts:/app/scripts \
  -v $(pwd)/src:/app/src \
  bike-demand-training:latest \
  python scripts/backfill_historical_data.py

# 2. Backfill weather data (Oct-Dec 2025)
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -v $(pwd)/scripts:/app/scripts \
  -v $(pwd)/src:/app/src \
  bike-demand-training:latest \
  python scripts/backfill_weather.py

# 3. Generate features (10K feature records with 22 features)
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -v $(pwd)/scripts:/app/scripts \
  -v $(pwd)/src:/app/src \
  bike-demand-training:latest \
  python scripts/generate_features.py
```

### Step 7: Train Production Models

```bash
# Build training Docker image
docker build -t bike-demand-training:latest -f docker/training/Dockerfile .

# Run training (trains XGBoost + LightGBM, promotes best to Production)
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-training:latest
```

**Expected Output:**
```
✓ XGBoost - Test RMSE: 0.63
✓ LightGBM - Test RMSE: 0.61
✅ Model version 5 promoted to Production!
Model: bike-demand-forecasting v5
Stage: Production
```

### Step 8: View Results in MLflow

1. Open http://localhost:5000
2. Click "Experiments" → "bike-demand-production"
3. See both XGBoost and LightGBM runs with metrics
4. Click "Models" → "bike-demand-forecasting"
5. See Production model (LightGBM v5)

### Step 9: Launch Streamlit Dashboard

```bash
# Build dashboard Docker image
docker build -t bike-demand-dashboard:latest -f docker/dashboard/Dockerfile .

# Run dashboard
docker run --rm -p 8501:8501 \
  --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-dashboard:latest
```

**Access Dashboard**: http://localhost:8501

The dashboard includes 4 pages:
1. **🔮 Demand Forecast** - Select station and view predictions
2. **📊 Model Performance** - View model metrics and comparison
3. **✅ Data Quality** - Monitor data drift and quality
4. **💓 System Health** - Check infrastructure status

## Production Files & Scripts

### Essential Production Scripts

Located in [scripts/](scripts/):

1. **[backfill_historical_data.py](scripts/backfill_historical_data.py:1)** - Downloads NYC Citi Bike trip data and reconstructs station availability
2. **[backfill_weather.py](scripts/backfill_weather.py:1)** - Fetches historical weather from Open-Meteo API (free)
3. **[generate_features.py](scripts/generate_features.py:1)** - Engineers 22 time-series features
4. **[train_production_model.py](scripts/train_production_model.py:1)** - Trains XGBoost/LightGBM and registers to MLflow

### Docker Images

All services run in Docker containers:

1. **bike-demand-training** - ML training pipeline
2. **bike-demand-api** - FastAPI server
3. **bike-demand-dashboard** - Streamlit dashboard
4. **bike-demand-airflow** - Airflow scheduler/webserver

Build all images:

```bash
docker build -t bike-demand-training:latest -f docker/training/Dockerfile .
docker build -t bike-demand-api:latest -f docker/api/Dockerfile .
docker build -t bike-demand-dashboard:latest -f docker/dashboard/Dockerfile .
docker build -t bike-demand-airflow:latest -f docker/airflow/Dockerfile .
```

## Streamlit Dashboard

### Running the Dashboard

The Streamlit dashboard provides an interactive web interface for:
- Viewing bike demand forecasts
- Monitoring model performance
- Checking data quality
- System health monitoring

**Start Dashboard:**

```bash
# Option 1: Using Docker (Recommended)
docker run --rm -p 8501:8501 \
  --network host \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-dashboard:latest

# Option 2: Using docker-compose (if configured in docker-compose.yml)
cd infrastructure
docker-compose up dashboard

# Option 3: Local Python (for development)
streamlit run dashboard/app.py
```

**Access**: http://localhost:8501

### Dashboard Features

#### 1. 🔮 Demand Forecast Page

**Make Predictions:**

1. **Select Station**
   - Use dropdown to choose from active bike stations
   - View station details (capacity, location)

2. **Choose Forecast Horizon**
   - 1 hour ahead
   - 6 hours ahead
   - 24 hours ahead (full day)

3. **View Predictions**
   - Interactive charts showing predicted demand
   - Confidence intervals
   - Historical comparison

**Features:**
- Real-time predictions from Production model
- Station map with availability heatmap
- Demand trends by hour/day
- Peak hours identification

#### 2. 📊 Model Performance Page

**Monitor ML Models:**

- **Current Production Model**
  - Model name and version
  - Test metrics (RMSE, MAE, R², MAPE)
  - Training timestamp

- **Model Comparison**
  - Compare all trained models
  - Performance charts (RMSE over time)
  - Feature importance plots

- **Experiment History**
  - View all MLflow experiments
  - Filter by date/metrics
  - Download model artifacts

#### 3. ✅ Data Quality Page

**Monitor Data Health:**

- **Data Completeness**
  - Missing values analysis
  - Data coverage by hour/day
  - Station uptime statistics

- **Feature Distribution**
  - Histogram of key features
  - Outlier detection
  - Statistical summaries

- **Data Drift Detection** (using Evidently AI)
  - Feature drift scores
  - Alerts when drift > threshold
  - Drift visualization

#### 4. 💓 System Health Page

**Infrastructure Monitoring:**

- **Service Status**
  - PostgreSQL: Connection pool, query performance
  - MLflow: Available models, experiments count
  - Airflow: DAG status, last run times

- **Database Stats**
  - Total records by table
  - Data growth over time
  - Storage usage

- **System Metrics**
  - API response times (if running)
  - Prediction latency
  - Error rates

### Making Predictions via Dashboard

**Step-by-Step:**

1. **Open Dashboard**
   ```bash
   # Navigate to http://localhost:8501
   ```

2. **Go to "🔮 Demand Forecast" Page**
   - Click on sidebar navigation

3. **Select a Station**
   - Choose from dropdown: "Select a bike station"
   - Example: "Central Park S & 6 Ave"

4. **Choose Prediction Timeframe**
   - Select radio button: "1 hour", "6 hours", or "24 hours"

5. **View Forecast**
   - See interactive Plotly chart
   - Hover over points for exact values
   - Download chart as PNG

6. **Interpret Results**
   - **Green zone**: High availability (>10 bikes)
   - **Yellow zone**: Moderate availability (5-10 bikes)
   - **Red zone**: Low availability (<5 bikes)

**Example Output:**
```
Station: Central Park S & 6 Ave
Current Time: 2025-12-26 14:30:00
Predicted Demand (1h ahead): 8 bikes
Confidence Interval: [6, 10] bikes
Recommendation: Station will have moderate availability
```

### Dashboard Configuration

**Environment Variables:**

```bash
# Database connection
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_DATABASE=bike_demand_db

# MLflow server
MLFLOW_TRACKING_URI=http://localhost:5000

# Optional: API endpoint (if running)
API_BASE_URL=http://localhost:8000
```

**Streamlit Config** (`.streamlit/config.toml`):

```toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#1E88E5"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### Dashboard Screenshots

**Home Page:**
- Overview of system status
- Quick metrics (total stations, predictions count, model accuracy)
- Recent predictions table

**Forecast Page:**
- Station selector dropdown
- Interactive demand chart
- Map view with station locations
- Historical comparison

**Performance Page:**
- Model metrics cards
- RMSE/MAE/R² trend charts
- Feature importance bar chart
- Experiment comparison table

### Troubleshooting Dashboard

**Dashboard won't start:**
```bash
# Check if port 8501 is available
lsof -i :8501

# Check database connection
docker exec bike_demand_postgres pg_isready
```

**"No data found" errors:**
```bash
# Verify data is loaded
docker exec -it bike_demand_postgres psql -U postgres -d bike_demand_db -c "SELECT COUNT(*) FROM features;"

# Should return > 0 rows
```

**MLflow connection errors:**
```bash
# Test MLflow is reachable
curl http://localhost:5000/health

# Verify model exists
curl http://localhost:5000/api/2.0/mlflow/registered-models/list
```

**Slow dashboard performance:**
- Reduce forecast horizon (use 1h instead of 24h)
- Limit data range in queries
- Check database indexes are created

## Project Structure

```
bike-demand-prediction/
├── src/                          # Source code (12 modules)
│   ├── config/                   # Database & settings
│   ├── data/                     # Data collectors & processors
│   ├── features/                 # Feature engineering
│   ├── models/                   # ML model implementations
│   ├── training/                 # Training pipeline
│   ├── serving/api/              # FastAPI application
│   └── monitoring/               # Drift detection
├── airflow/dags/                 # 4 Airflow DAGs
│   ├── data_ingestion_dag.py          # 15-min data collection
│   ├── weather_enrichment_dag.py      # 30-min weather updates
│   ├── feature_engineering_dag.py     # Hourly feature generation
│   └── model_training_dag.py          # Daily model retraining
├── dashboard/                    # Streamlit dashboard
│   ├── app.py                    # Main dashboard
│   └── pages/                    # 4 dashboard pages
├── docker/                       # Dockerfiles for all services
│   ├── training/Dockerfile
│   ├── api/Dockerfile
│   ├── dashboard/Dockerfile
│   └── airflow/Dockerfile
├── infrastructure/               # Production deployment
│   ├── docker-compose.yml        # Multi-service orchestration
│   └── postgres/                 # Database schema
├── scripts/                      # 4 essential production scripts
├── config/                       # Feature & model configs
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # Detailed architecture guide
│   └── START_PRODUCTION.md       # Production setup guide
├── .github/workflows/            # CI/CD pipelines
│   ├── ci.yml                    # Build & validate
│   ├── cd.yml                    # Deploy
│   └── model-training.yml        # Weekly training
└── pyproject.toml                # Python dependencies
```

## Data Pipeline

### Data Sources

1. **NYC Citi Bike Historical Data**
   - Source: S3 bucket (`s3.amazonaws.com/tripdata/`)
   - Format: Monthly ZIP files with trip data
   - Records: 50,000 station status snapshots (Nov 2025)
   - No authentication required

2. **Open-Meteo Historical Weather API**
   - Source: `archive-api.open-meteo.com`
   - Free tier: Unlimited requests
   - Records: 1,369 hourly weather observations (Oct-Dec 2025)
   - Variables: Temperature, humidity, wind speed, precipitation

### Engineered Features (22 total)

**Temporal Features:**
- `hour_of_day` (0-23)
- `day_of_week` (0-6)
- `day_of_month` (1-31)
- `month` (1-12)
- `is_weekend` (boolean)
- `is_business_hours` (9 AM - 5 PM)
- `is_morning_rush` (7-9 AM)
- `is_evening_rush` (5-7 PM)

**Lag Features:**
- `bikes_lag_1h`, `bikes_lag_6h`, `bikes_lag_24h`
- `docks_lag_1h`, `docks_lag_6h`, `docks_lag_24h`

**Rolling Statistics:**
- `bikes_rolling_mean_3h`, `bikes_rolling_mean_6h`
- `bikes_rolling_std_3h`, `bikes_rolling_std_6h`

**Weather Features:**
- `temperature`, `humidity`, `wind_speed`, `precipitation`

**Target:**
- `bikes_available` (regression target)

### Database Schema

All data stored in PostgreSQL:

```sql
-- Station metadata
bike_stations (station_id, name, latitude, longitude, capacity)

-- Historical status
bike_station_status (station_id, timestamp, bikes_available, docks_available)

-- Weather data
weather_data (timestamp, temperature, humidity, wind_speed, precipitation)

-- Engineered features
features (station_id, timestamp, feature_json JSONB, feature_version)

-- Model predictions
predictions (station_id, prediction_timestamp, predicted_demand, model_version)

-- Performance metrics
model_performance (model_name, model_version, rmse, mae, r2_score)
```

## Machine Learning Models

### Production Models

| Model | Test RMSE | Test R² | Training Time | Status |
|-------|-----------|---------|---------------|--------|
| **LightGBM** | **0.61** | **0.631** | 2.4s | ✅ Production |
| **XGBoost** | 0.63 | 0.609 | 3.5s | Staged |

### Model Training Configuration

```python
# LightGBM (Best Model)
{
    'n_estimators': 200,
    'max_depth': 8,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}

# XGBoost
{
    'n_estimators': 200,
    'max_depth': 8,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}
```

### Train/Val/Test Split

- **Training**: 70% (7,004 samples)
- **Validation**: 15% (1,496 samples)
- **Test**: 15% (1,500 samples)
- **NO SHUFFLING** (time-series data)

### Evaluation Metrics

```
LightGBM Production Model:
- Test RMSE: 0.61 bikes
- Test MAE: 0.36 bikes
- Test R²: 0.6309
- Test MAPE: 3.6%
```

## Monitoring

### MLflow Experiment Tracking

All training runs logged to MLflow:
- Parameters (hyperparameters)
- Metrics (RMSE, MAE, R², MAPE)
- Model artifacts
- Versioning & staging

### Model Registry

Production model workflow:
1. Train XGBoost + LightGBM
2. Compare test RMSE
3. Best model promoted to "Production" stage
4. Previous model archived

### System Monitoring

**Prometheus Metrics** (http://localhost:9090):
- Database connection pool
- Airflow DAG runs
- API latency (when API running)

**Grafana Dashboards** (http://localhost:3000):
- System health
- Model performance over time
- Data quality metrics

## CI/CD Pipeline

### GitHub Actions Workflows

1. **[CI - Build & Validate](.github/workflows/ci.yml:1)**
   - Lint code (black, flake8, isort)
   - Build all 4 Docker images
   - Validate project structure
   - Security scans (safety, bandit)

2. **[CD - Deploy](.github/workflows/cd.yml:1)**
   - Build production images
   - Push to GitHub Container Registry
   - Deploy to staging/production

3. **[Model Training](.github/workflows/model-training.yml:1)**
   - Weekly schedule (Sundays 2 AM UTC)
   - Run training in Docker container
   - Validate model performance
   - Promote best model to Production

## Production Deployment

### Docker Compose Deployment

```bash
cd infrastructure
docker-compose up -d
```

Services started:
- ✅ PostgreSQL (2 instances: main + airflow)
- ✅ MLflow Server
- ✅ Airflow Webserver + Scheduler
- ✅ Prometheus
- ✅ Grafana

### Health Checks

```bash
# Check all services
docker ps --format "{{.Names}}: {{.Status}}"

# Test MLflow
curl http://localhost:5000/health
# Output: OK

# Test Airflow
curl http://localhost:8080/health
# Output: {"metadatabase": {"status": "healthy"}, ...}
```

### Logs

```bash
# View all logs
docker-compose logs -f

# Specific service
docker logs bike_demand_mlflow -f
docker logs bike_demand_airflow_scheduler -f
```

### Shutdown

```bash
cd infrastructure
docker-compose down         # Stop containers
docker-compose down -v      # Stop & remove volumes (⚠️ deletes data)
```

## Troubleshooting

### MLflow shows "unhealthy"

MLflow healthcheck uses Python (no curl/wget in container). It may take 60s to pass healthcheck but will work immediately:

```bash
# Test manually
curl http://localhost:5000/health
# Should return: OK
```

### Training fails with "connection refused"

Use `--network host` mode for training container:

```bash
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  bike-demand-training:latest
```

### Airflow DAGs not showing

1. Check Airflow webserver is healthy: `docker ps`
2. Check logs: `docker logs bike_demand_airflow_scheduler`
3. Verify DAG files exist: `ls airflow/dags/`

### Database connection errors

Ensure PostgreSQL is healthy:

```bash
docker exec bike_demand_postgres pg_isready
# Should output: postgres is ready
```

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - Detailed system architecture, pipelines, and design decisions
- **[Production Setup](docs/START_PRODUCTION.md)** - Complete production deployment guide

## Project Metrics

- ✅ **Docker Images**: 4 (training, api, dashboard, airflow)
- ✅ **Running Services**: 7 containers
- ✅ **Production Scripts**: 4 essential scripts
- ✅ **ML Models**: 2 (XGBoost + LightGBM)
- ✅ **Features**: 22 engineered features
- ✅ **Data Records**: 50K bike status + 1.4K weather + 10K features
- ✅ **Test RMSE**: 0.61 bikes (LightGBM)
- ✅ **Airflow DAGs**: 4 automated pipelines
- ✅ **CI/CD**: 3 GitHub Actions workflows

## Interview Talking Points

**"I built a Level 2 MLOps production system for bike demand forecasting using real NYC Citi Bike data:"**

1. **End-to-End Pipeline**: "Backfilled 50K historical bike station records, enriched with weather data, engineered 22 time-series features including lags and rolling statistics, and trained ensemble models achieving RMSE 0.61"

2. **Docker-First Architecture**: "100% containerized system with 7 services orchestrated via Docker Compose - can deploy to any environment in minutes with zero configuration drift"

3. **Production ML**: "Built automated training pipeline in Docker that loads features from PostgreSQL, trains XGBoost and LightGBM models, evaluates performance, and automatically promotes the best model to MLflow Production stage"

4. **MLOps Best Practices**: "Implemented experiment tracking with MLflow, model registry with versioning, automated DAGs with Airflow, and multi-layer monitoring with Prometheus/Grafana"

5. **Real-World Data**: "Used actual NYC Citi Bike historical trip data (3.4M trips) and free Open-Meteo weather API - no synthetic data, fully reproducible with public APIs"

## License

Apache License 2.0 - see [LICENSE](LICENSE) file.

## Acknowledgments

- NYC Citi Bike for open bike-sharing data
- Open-Meteo for free historical weather API
- MLflow, Airflow, and open-source ML community

---

**Made with Docker 🐳 | Built for Production 🚀 | Ready for Interviews 💼**
