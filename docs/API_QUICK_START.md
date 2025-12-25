# FastAPI Quick Start Guide

Production-grade REST API for bike demand prediction serving.

## 🚀 Quick Start

### Prerequisites

1. Python 3.11+
2. PostgreSQL running (from docker-compose)
3. MLflow server running (from docker-compose)
4. Trained model in MLflow registry

### Start the API

```bash
# From project root
python src/serving/api/main.py
```

Or with uvicorn directly:

```bash
uvicorn src.serving.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify API is Running

```bash
curl http://localhost:8000/health
```

### Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📋 API Endpoints

### Prediction Endpoints

#### Single Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "station_1",
    "timestamp": "2025-01-15T14:00:00",
    "weather_data": {
      "temperature": 20.0,
      "humidity": 65,
      "wind_speed": 5.0,
      "weather_condition": "Clear"
    }
  }'
```

Response:
```json
{
  "station_id": "station_1",
  "timestamp": "2025-01-15T14:00:00",
  "predicted_demand": 12.5,
  "confidence_interval": {
    "lower": 9.8,
    "upper": 15.2,
    "confidence_level": 0.95
  },
  "model_info": {
    "name": "bike-demand-forecasting",
    "version": "3",
    "stage": "Production"
  },
  "prediction_made_at": "2025-01-15T13:00:00"
}
```

#### Batch Prediction

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "predictions": [
      {
        "station_id": "station_1",
        "timestamp": "2025-01-15T14:00:00"
      },
      {
        "station_id": "station_2",
        "timestamp": "2025-01-15T14:00:00"
      }
    ]
  }'
```

#### Multi-hour Forecast

```bash
# POST method
curl -X POST http://localhost:8000/predict/station/station_1/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "hours_ahead": 24
  }'

# GET method (simpler)
curl "http://localhost:8000/predict/station/station_1/forecast?hours_ahead=24"
```

Response:
```json
{
  "station_id": "station_1",
  "forecast_start": "2025-01-15T12:00:00",
  "forecast_hours": 24,
  "forecasts": [
    {
      "timestamp": "2025-01-15T13:00:00",
      "hour_ahead": 1,
      "predicted_demand": 12.5,
      "confidence_interval": {
        "lower": 9.8,
        "upper": 15.2,
        "confidence_level": 0.95
      }
    }
  ],
  "model_info": {...},
  "forecast_made_at": "2025-01-15T12:00:00"
}
```

### Health Check Endpoints

#### Basic Health Check

```bash
curl http://localhost:8000/health
```

#### Detailed Health Check

```bash
curl http://localhost:8000/health/detailed
```

#### Kubernetes Probes

```bash
# Readiness probe (is service ready to accept traffic?)
curl http://localhost:8000/health/ready

# Liveness probe (is service alive?)
curl http://localhost:8000/health/live
```

### Monitoring Endpoints

#### Current Model Information

```bash
curl http://localhost:8000/monitoring/models/current
```

#### Prometheus Metrics

```bash
curl http://localhost:8000/monitoring/metrics
```

#### Reload Production Model

```bash
curl -X POST http://localhost:8000/monitoring/models/reload
```

## 🧪 Testing

Run the comprehensive API test suite:

```bash
# Start the API first
python src/serving/api/main.py

# In another terminal, run tests
python scripts/test_api.py
```

## 🐳 Docker Deployment

### Build Image

```bash
docker build -f docker/api/Dockerfile -t bike-demand-api:latest .
```

### Run Container

```bash
docker run -d \
  --name bike-demand-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@postgres:5432/bike_demand" \
  -e MLFLOW_TRACKING_URI="http://mlflow:5000" \
  bike-demand-api:latest
```

### Using Docker Compose

The API is already configured in `docker-compose.yml`:

```bash
docker-compose up api
```

## 📊 Example Workflows

### Workflow 1: Get Current Model Info

```python
import requests

# Get current model
response = requests.get("http://localhost:8000/monitoring/models/current")
model_info = response.json()

print(f"Model: {model_info['model_info']['name']}")
print(f"Version: {model_info['model_info']['version']}")
print(f"Test RMSE: {model_info['metrics']['test_rmse']}")
```

### Workflow 2: Make Prediction with Weather

```python
import requests
from datetime import datetime, timedelta

# Prediction 1 hour ahead
prediction_time = datetime.utcnow() + timedelta(hours=1)

payload = {
    "station_id": "station_1",
    "timestamp": prediction_time.isoformat(),
    "weather_data": {
        "temperature": 18.5,
        "humidity": 65,
        "wind_speed": 4.2,
        "weather_condition": "Clear"
    }
}

response = requests.post("http://localhost:8000/predict", json=payload)
result = response.json()

print(f"Predicted demand: {result['predicted_demand']:.2f} bikes")
print(f"Confidence interval: [{result['confidence_interval']['lower']:.2f}, {result['confidence_interval']['upper']:.2f}]")
```

### Workflow 3: Generate 24-hour Forecast

```python
import requests
import pandas as pd

# Get forecast
response = requests.get(
    "http://localhost:8000/predict/station/station_1/forecast",
    params={"hours_ahead": 24}
)
forecast = response.json()

# Convert to DataFrame for analysis
df = pd.DataFrame(forecast['forecasts'])
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(df[['timestamp', 'predicted_demand', 'hour_ahead']].head())

# Plot
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['predicted_demand'], marker='o')
plt.fill_between(
    df['timestamp'],
    df['confidence_interval'].apply(lambda x: x['lower']),
    df['confidence_interval'].apply(lambda x: x['upper']),
    alpha=0.2
)
plt.title('24-hour Bike Demand Forecast')
plt.xlabel('Time')
plt.ylabel('Predicted Bikes Available')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### Workflow 4: Batch Predictions for Dashboard

```python
import requests
from datetime import datetime, timedelta

# Get predictions for top 10 stations
stations = [f"station_{i}" for i in range(1, 11)]
prediction_time = datetime.utcnow() + timedelta(hours=1)

payload = {
    "predictions": [
        {"station_id": station_id, "timestamp": prediction_time.isoformat()}
        for station_id in stations
    ]
}

response = requests.post("http://localhost:8000/predict/batch", json=payload)
results = response.json()

print(f"Successful: {results['successful']}/{results['total_predictions']}")

for pred in results['predictions']:
    print(f"{pred['station_id']}: {pred['predicted_demand']:.2f} bikes")
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bike_demand

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Logging
LOG_LEVEL=INFO
```

### Model Configuration

The API automatically loads the production model from MLflow registry. To use a specific version:

```python
from src.serving.model_loader import get_model_loader

loader = get_model_loader()
loader.load_specific_version("bike-demand-forecasting", version="5")
```

## 🚨 Troubleshooting

### Model Not Loaded

**Error**: `No model loaded`

**Solution**:
1. Check MLflow server is running
2. Verify model exists in registry: `mlflow models list`
3. Ensure model is in Production stage
4. Manually reload: `curl -X POST http://localhost:8000/monitoring/models/reload`

### Database Connection Failed

**Error**: `Database connection failed`

**Solution**:
1. Verify PostgreSQL is running
2. Check DATABASE_URL in `.env`
3. Test connection: `psql $DATABASE_URL`

### Prediction Fails

**Error**: `Prediction failed: No historical data`

**Solution**:
1. Run data collection DAG first
2. Wait for feature engineering DAG
3. Ensure at least 7 days of data exists

## 📈 Performance

- **Latency**: < 100ms for single predictions
- **Throughput**: ~100 predictions/second
- **Batch Size**: Max 100 predictions per request
- **Forecast Horizon**: Max 168 hours (7 days)

## 🔗 Integration with Other Components

### Streamlit Dashboard

The dashboard uses these API endpoints:

```python
# In dashboard/app.py
API_URL = "http://api:8000"  # Docker service name

# Get forecast
forecast = requests.get(f"{API_URL}/predict/station/{station_id}/forecast").json()
```

### Prometheus Monitoring

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'bike-demand-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/monitoring/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import metrics:
- `bike_demand_model_test_rmse` - Model performance
- `bike_demand_database_connected` - System health
- `bike_demand_model_loaded` - Model status

## 📚 Next Steps

1. ✅ **API is running** → Proceed to Streamlit dashboard
2. Set up CI/CD pipeline for automated deployment
3. Configure Prometheus + Grafana monitoring
4. Implement rate limiting and authentication
5. Add caching for frequently requested forecasts

## 🎯 Portfolio Highlights

When presenting this API in interviews:

1. **Production-Ready**: Health checks, monitoring, error handling
2. **MLOps Integration**: MLflow registry, model reloading
3. **Scalability**: Batch endpoints, async processing
4. **Observability**: Prometheus metrics, request logging
5. **Documentation**: Auto-generated OpenAPI/Swagger docs
6. **Best Practices**: Pydantic schemas, middleware, type hints

---

**GitHub Repository**: https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities

**API Documentation**: http://localhost:8000/docs
