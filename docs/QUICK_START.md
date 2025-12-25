# Quick Start Guide

Get the complete Bike Demand Prediction system running in 10 minutes.

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- 8GB RAM minimum
- Ports available: 5000, 5432, 8000, 8080, 8501

## 💡 Quick Tip: Docker Compose Shortcut

To avoid typing `-f infrastructure/docker-compose.yml` every time, create a symlink:

```bash
ln -s infrastructure/docker-compose.yml docker-compose.yml
```

Then you can use shorter commands like `docker-compose up -d postgres mlflow`.

This guide shows the full `-f` flag commands for clarity.

## 🚀 Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities.git
cd Bike-Demand-Prediction-for-Smart-Cities
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# At minimum, add your OpenWeatherMap API key
nano .env
```

Required in `.env`:
```bash
WEATHER_API_KEY=your_openweathermap_api_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bike_demand
MLFLOW_TRACKING_URI=http://localhost:5000
```

Get free API key: https://openweathermap.org/api

### 4. Start Infrastructure Services

```bash
# Start PostgreSQL and MLflow
docker-compose -f infrastructure/docker-compose.yml up -d postgres mlflow

# Wait for services to be ready (30 seconds)
sleep 30

# Verify PostgreSQL is running
docker-compose -f infrastructure/docker-compose.yml ps
```

### 5. Verify Database Initialization

The database schema is automatically created when PostgreSQL starts.

```bash
# Verify tables exist
docker-compose -f infrastructure/docker-compose.yml exec postgres psql -U postgres -d bike_demand_db -c "\dt"

# You should see 8 tables:
# - bike_stations, bike_station_status, weather_data, features
# - predictions, model_performance, data_quality_checks, api_logs
```

**Note**: If you need to manually reinitialize the schema:
```bash
# Using local psql (update DATABASE_URL in .env to: postgresql://postgres:postgres@localhost:5432/bike_demand_db)
psql postgresql://postgres:postgres@localhost:5432/bike_demand_db -f infrastructure/postgres/schema.sql

# Or using docker exec
docker-compose -f infrastructure/docker-compose.yml exec postgres psql -U postgres -d bike_demand_db -f /docker-entrypoint-initdb.d/02-schema.sql
```

### 6. Collect Initial Data

```bash
# Test data collection
python scripts/test_data_collection.py

# This will:
# - Fetch bike station data from NYC Citi Bike API
# - Collect weather data
# - Store in PostgreSQL
```

### 7. Generate Features

```bash
# Test feature engineering
python scripts/test_features.py

# This creates 100+ features from raw data
```

### 8. Train Initial Model

```bash
# Run training pipeline
python scripts/test_full_pipeline.py

# Or train directly
python -c "from src.training.train_pipeline import train_model; train_model()"
```

This will:
- Load data from feature store
- Train XGBoost model
- Evaluate on test set
- Log to MLflow
- Register best model

### 9. Start the API Server

```bash
# In a new terminal
python src/serving/api/main.py

# Or with uvicorn
uvicorn src.serving.api.main:app --reload --host 0.0.0.0 --port 8000
```

Verify API is running:
```bash
curl http://localhost:8000/health
```

API Documentation: http://localhost:8000/docs

### 10. Start the Dashboard

```bash
# In another terminal

# Configure dashboard secrets
cd dashboard/.streamlit
cp secrets.toml.example secrets.toml

# Run dashboard
cd ../..
streamlit run dashboard/app.py
```

Dashboard will open at: http://localhost:8501

## ✅ Verification

### Check All Services

```bash
# PostgreSQL
psql $DATABASE_URL -c "SELECT COUNT(*) FROM bike_stations;"

# MLflow
curl http://localhost:5000/health

# API
curl http://localhost:8000/health/detailed

# Dashboard
# Open http://localhost:8501 in browser
```

### Make a Test Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "station_1",
    "weather_data": {
      "temperature": 20,
      "humidity": 65
    }
  }'
```

## 🔄 Running with Airflow (Optional)

For automated pipelines:

```bash
# Start Airflow services
docker-compose -f infrastructure/docker-compose.yml up -d airflow-init
docker-compose -f infrastructure/docker-compose.yml up -d airflow-webserver airflow-scheduler

# Access Airflow UI
# http://localhost:8080
# User: airflow
# Password: airflow

# Enable DAGs:
# - data_ingestion (runs every 15 min)
# - weather_enrichment (runs every 30 min)
# - feature_engineering (runs every hour)
# - model_training (runs daily at 2 AM)
```

## 🐳 Full Docker Deployment

To run everything in Docker:

```bash
# Build all images
docker-compose -f infrastructure/docker-compose.yml build

# Start all services
docker-compose -f infrastructure/docker-compose.yml up -d

# Check status
docker-compose -f infrastructure/docker-compose.yml ps

# View logs
docker-compose -f infrastructure/docker-compose.yml logs -f api dashboard
```

Services will be available at:
- PostgreSQL: localhost:5432
- MLflow: http://localhost:5000
- Airflow: http://localhost:8080
- API: http://localhost:8000
- Dashboard: http://localhost:8501

## 📊 Using the System

### 1. Dashboard Navigation

**Main Page**
- System status overview
- Quick model metrics
- Navigation to features

**🔮 Demand Forecast**
- Generate forecasts for stations
- Batch predictions
- Export results

**📊 Model Performance**
- View model metrics
- Track performance history

**✅ Data Quality**
- Monitor data pipeline
- Check data freshness

**💓 System Health**
- Component status
- Service monitoring

### 2. API Usage

```python
import requests

# Get forecast
response = requests.get(
    "http://localhost:8000/predict/station/station_1/forecast",
    params={"hours_ahead": 24}
)
forecast = response.json()

# Batch predictions
response = requests.post(
    "http://localhost:8000/predict/batch",
    json={
        "predictions": [
            {"station_id": "station_1"},
            {"station_id": "station_2"}
        ]
    }
)
results = response.json()
```

### 3. MLflow Tracking

```bash
# View experiments
open http://localhost:5000

# Search models
mlflow models list

# Get production model
mlflow models get-model --name bike-demand-forecasting --version latest
```

## 🔧 Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose -f infrastructure/docker-compose.yml ps postgres

# Restart if needed
docker-compose -f infrastructure/docker-compose.yml restart postgres

# Check logs
docker-compose -f infrastructure/docker-compose.yml logs postgres
```

### API Not Starting

```bash
# Check if model is available
mlflow models list

# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# View API logs
python src/serving/api/main.py --log-level debug
```

### Dashboard Shows "API Offline"

```bash
# Verify API is running
curl http://localhost:8000/health

# Check dashboard secrets
cat dashboard/.streamlit/secrets.toml

# Restart dashboard
streamlit run dashboard/app.py --server.port 8501
```

### No Data in Dashboard

```bash
# Run data collection
python scripts/test_data_collection.py

# Generate features
python scripts/test_features.py

# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM bike_station_status;"
```

## 📈 Next Steps

### Daily Workflow

1. **Monitor Data** - Check dashboard "Data Quality" page
2. **Review Predictions** - Use "Demand Forecast" page
3. **Check Performance** - Monitor "Model Performance"
4. **System Health** - Verify all components are healthy

### Production Deployment

1. Set up CI/CD pipeline
2. Configure production environment variables
3. Enable model monitoring with Evidently AI
4. Set up Prometheus + Grafana dashboards
5. Configure backup and disaster recovery
6. Implement rate limiting and authentication

### Advanced Features

1. **A/B Testing** - Test multiple models in production
2. **Real-time Streaming** - Add Kafka for live updates
3. **Multi-city Support** - Expand to other bike systems
4. **Explainability** - Add SHAP values for predictions
5. **API Tiers** - Implement free/premium with rate limiting

## 📚 Documentation

- [API Documentation](./API_QUICK_START.md)
- [Dashboard README](../dashboard/README.md)
- [Architecture](./ARCHITECTURE.md) *(coming soon)*
- [Deployment Guide](./DEPLOYMENT.md) *(coming soon)*

## 🆘 Getting Help

- **GitHub Issues**: https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues
- **API Docs**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000
- **Airflow UI**: http://localhost:8080

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Sources                             │
│  NYC Citi Bike API (GBFS)    │    OpenWeatherMap API             │
└──────────────┬───────────────┴──────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Airflow DAGs (Orchestration)                  │
│  Data Ingestion (15min) │ Weather (30min) │ Features (hourly)   │
│  Model Training (daily at 2 AM)                                  │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PostgreSQL Database                         │
│  Stations │ Status │ Weather │ Features (JSONB) │ Predictions    │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ├──────────────┬─────────────────┬──────────────────┐
               ▼              ▼                 ▼                  ▼
       ┌──────────────┐ ┌──────────┐    ┌──────────┐      ┌──────────┐
       │  Feature     │ │ Training │    │  MLflow  │      │   API    │
       │ Engineering  │ │ Pipeline │    │ Registry │      │ Server   │
       │   (100+)     │ │ XGB/LGBM │    │  Models  │      │ FastAPI  │
       └──────────────┘ └────┬─────┘    └────┬─────┘      └────┬─────┘
                             │               │                  │
                             └───────────────┴──────────────────┤
                                                                 ▼
                                                          ┌────────────┐
                                                          │ Dashboard  │
                                                          │ Streamlit  │
                                                          └────────────┘
```

## 🎯 Success Criteria

✅ All services running
✅ Data collection working
✅ Features generated
✅ Model trained and registered
✅ API responding to predictions
✅ Dashboard displaying forecasts

**Estimated Setup Time**: 10-15 minutes

**Estimated Training Time**: 2-5 minutes (depending on data size)

---

**Repository**: https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities

**Built with**: Python • FastAPI • Streamlit • MLflow • Airflow • PostgreSQL • Docker
