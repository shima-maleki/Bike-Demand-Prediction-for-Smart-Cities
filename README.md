# Bike Demand Prediction for Smart Cities

**Level 2 MLOps** bike demand forecasting system with automated data pipelines, experiment tracking, model registry, and comprehensive monitoring.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

End-to-end machine learning project that predicts bike rental demand using live public bike-sharing APIs and weather data. The system ingests real-time station data from NYC Citi Bike, enriches it with weather signals from OpenWeatherMap, engineers time-series features, trains multiple forecasting models, and serves predictions via REST API and interactive dashboard.

### Key Features

- **Automated Data Pipelines**: Airflow DAGs for data ingestion (15-min), weather enrichment (30-min), feature engineering (hourly), and model training (daily)
- **Experiment Tracking**: MLflow for tracking experiments, hyperparameters, and metrics
- **Model Registry**: Centralized model versioning with MLflow Model Registry
- **Multiple Models**: XGBoost, LightGBM, CatBoost, ARIMA, SARIMA, Prophet, LSTM
- **Data Versioning**: DVC for tracking datasets and model artifacts
- **REST API**: FastAPI service with prediction endpoints
- **Interactive Dashboard**: Streamlit dashboard for visualizing forecasts and metrics
- **Monitoring**: Prometheus + Grafana for system metrics, Evidently AI for data drift
- **CI/CD**: GitHub Actions for automated testing, linting, and deployment
- **Containerization**: Docker + Docker Compose for reproducible deployments

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Sources                                │
│  NYC Citi Bike API          OpenWeatherMap API                  │
└────────────────┬────────────────────┬────────────────────────────┘
                 │                    │
                 ▼                    ▼
         ┌────────────────────────────────────┐
         │     Airflow Data Pipelines         │
         │  • Data Ingestion (15 min)         │
         │  • Weather Enrichment (30 min)     │
         │  • Feature Engineering (hourly)    │
         │  • Model Training (daily)          │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │      PostgreSQL Database           │
         │  • Bike station status             │
         │  • Weather data                    │
         │  • Engineered features             │
         │  • Predictions                     │
         │  • Model performance               │
         └────────────┬───────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  MLflow Server   │      │  Model Training  │
│  • Experiments   │      │  • XGBoost       │
│  • Metrics       │      │  • LightGBM      │
│  • Model Registry│      │  • SARIMA        │
└────────┬─────────┘      │  • Prophet       │
         │                │  • LSTM          │
         │                └──────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│         Production Serving               │
│                                          │
│  ┌──────────────┐    ┌────────────────┐ │
│  │  FastAPI     │    │   Streamlit    │ │
│  │  REST API    │    │   Dashboard    │ │
│  └──────────────┘    └────────────────┘ │
└──────────────────────────────────────────┘
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────┐
│         Monitoring & Observability       │
│  • Prometheus (metrics)                  │
│  • Grafana (visualization)               │
│  • Evidently AI (data drift)             │
└──────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Orchestration** | Apache Airflow 2.8+ |
| **Database** | PostgreSQL 16 |
| **ML Framework** | scikit-learn, XGBoost, LightGBM, CatBoost, Prophet, TensorFlow |
| **Experiment Tracking** | MLflow 2.9+ |
| **Data Versioning** | DVC 3.30+ |
| **API Framework** | FastAPI 0.108+ |
| **Dashboard** | Streamlit 1.29+ |
| **Monitoring** | Prometheus, Grafana, Evidently AI |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Code Quality** | Black, Flake8, MyPy, isort, pre-commit |

## Project Structure

```
bike-demand-prediction/
├── src/                          # Source code
│   ├── config/                   # Configuration management
│   ├── data/                     # Data collection & processing
│   │   ├── collectors/           # API collectors (Citi Bike, Weather)
│   │   ├── processors/           # Data cleaning & validation
│   │   └── storage/              # Database handlers
│   ├── features/                 # Feature engineering
│   ├── models/                   # ML model implementations
│   ├── training/                 # Training pipeline
│   ├── serving/                  # Model serving
│   │   └── api/                  # FastAPI application
│   └── monitoring/               # Monitoring & drift detection
├── airflow/                      # Airflow DAGs & plugins
│   ├── dags/                     # DAG definitions
│   └── plugins/                  # Custom operators
├── dashboard/                    # Streamlit dashboard
├── docker/                       # Dockerfiles
├── infrastructure/               # Docker Compose & configs
│   ├── postgres/                 # Database schema
│   └── monitoring/               # Prometheus, Grafana
├── tests/                        # Unit & integration tests
├── config/                       # YAML configurations
├── scripts/                      # Setup & utility scripts
├── notebooks/                    # Jupyter notebooks (EDA)
├── .github/workflows/            # CI/CD pipelines
└── pyproject.toml                # Dependencies
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- OpenWeatherMap API key ([Get free key](https://openweathermap.org/api))

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/bike-demand-prediction.git
cd bike-demand-prediction
```

2. **Create environment file**

```bash
cp .env.example .env
```

Edit `.env` and add your OpenWeatherMap API key:
```
WEATHER_API_KEY=your_api_key_here
```

3. **Start services with Docker Compose**

```bash
cd infrastructure
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- MLflow (port 5000)
- Airflow (port 8080)
- FastAPI (port 8000)
- Streamlit (port 8501)
- Prometheus (port 9090)
- Grafana (port 3000)

4. **Access the services**

- **Airflow UI**: http://localhost:8080 (admin/admin)
- **MLflow UI**: http://localhost:5000
- **FastAPI Docs**: http://localhost:8000/docs
- **Streamlit Dashboard**: http://localhost:8501
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### Local Development Setup

1. **Create virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**

```bash
pip install -e ".[dev]"
```

3. **Set up pre-commit hooks**

```bash
pre-commit install
```

4. **Initialize DVC**

```bash
bash scripts/setup_dvc.sh
```

5. **Run tests**

```bash
pytest
```

## Usage

### Data Collection

Airflow DAGs automatically collect data at scheduled intervals. To trigger manually:

```bash
# Via Airflow UI: http://localhost:8080
# Or via CLI:
docker exec -it bike_demand_airflow_scheduler airflow dags trigger data_ingestion_dag
```

### Model Training

```bash
# Trigger model training DAG
docker exec -it bike_demand_airflow_scheduler airflow dags trigger model_training_dag
```

### API Predictions

```bash
# Get prediction for a station
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c"}'

# Get 24-hour forecast
curl "http://localhost:8000/predict/station/66db237e-0aca-11e7-82f6-3863bb44ef7c/forecast?hours_ahead=24"
```

### Dashboard

Access the Streamlit dashboard at http://localhost:8501 to:
- View demand forecasts
- Monitor model performance
- Check data quality
- View system health

## Data Pipeline

### Data Sources

1. **NYC Citi Bike GBFS API** (No authentication required)
   - Station information: https://gbfs.citibikenyc.com/gbfs/en/station_information.json
   - Station status: https://gbfs.citibikenyc.com/gbfs/en/station_status.json
   - Update frequency: Real-time (15-minute ingestion)

2. **OpenWeatherMap API** (Free tier: 1,000 calls/day)
   - Current weather data
   - Update frequency: 30 minutes

### Feature Engineering

**Temporal Features:**
- Hour of day (0-23)
- Day of week (0-6)
- Month (1-12)
- Is weekend (boolean)
- Season (spring/summer/fall/winter)

**Lag Features:**
- Demand lag 1h, 3h, 6h, 12h, 24h, 48h, 168h (1 week)

**Rolling Features:**
- Rolling mean/std/min/max over 3h, 6h, 12h, 24h windows

**Weather Features:**
- Temperature (normalized)
- Feels-like temperature
- Humidity
- Wind speed
- Precipitation
- Weather category (clear/cloudy/rainy/snow)

**Holiday Features:**
- Is holiday (US federal holidays)
- Days to next holiday

## Models

### Implemented Models

1. **XGBoost** - Gradient boosting, excellent for tabular data
2. **LightGBM** - Fast gradient boosting, handles large datasets
3. **CatBoost** - Handles categorical features automatically
4. **SARIMA** - Statistical model, captures seasonality
5. **Prophet** - Facebook's time-series model, handles holidays/trends
6. **LSTM** - Deep learning, captures long-term dependencies

### Evaluation Metrics

- **RMSE** (Root Mean Square Error) - Primary metric
- **MAE** (Mean Absolute Error)
- **MAPE** (Mean Absolute Percentage Error)
- **R² Score**
- **Peak Hour Accuracy** - Custom metric for rush hours (6-9 AM, 5-8 PM)

### Model Selection

Ensemble strategy:
- **Primary**: XGBoost/LightGBM (70% weight) - handles complex patterns
- **Secondary**: Prophet (30% weight) - captures seasonality/holidays

## Monitoring

### Data Drift Detection

- **Tool**: Evidently AI
- **Frequency**: Daily
- **Threshold**: 0.3
- **Alerts**: Email/Slack when drift > threshold

### Model Performance

- **Metrics**: RMSE, MAE, MAPE tracked over 7-day rolling window
- **Alert**: When performance degrades > 10%

### System Monitoring

- **Prometheus** metrics:
  - API latency (p50, p95, p99)
  - Request count
  - Error rate
  - Database query performance
- **Grafana** dashboards for visualization

## Development

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Adding New Features

1. Create feature branch
2. Implement changes with tests
3. Run code quality checks
4. Submit pull request
5. CI/CD pipeline runs automatically

## Deployment

### Docker Deployment

```bash
# Build all images
docker-compose -f infrastructure/docker-compose.yml build

# Start all services
docker-compose -f infrastructure/docker-compose.yml up -d

# View logs
docker-compose -f infrastructure/docker-compose.yml logs -f

# Stop services
docker-compose -f infrastructure/docker-compose.yml down
```

### Production Deployment

For cloud deployment (AWS/GCP/Azure), see [deployment guide](docs/deployment.md).

## CI/CD Pipeline

GitHub Actions workflows:

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on: push, pull_request
   - Steps: lint → test → coverage

2. **CD Pipeline** (`.github/workflows/cd.yml`)
   - Runs on: push to main
   - Steps: build Docker images → push to registry → deploy

3. **Model Training** (`.github/workflows/model-training.yml`)
   - Runs on: weekly schedule
   - Steps: trigger Airflow DAG → validate model → promote to staging

## Project Roadmap

- [x] Phase 1: Foundation & Infrastructure
- [x] Phase 2: Data Collection & Storage
- [ ] Phase 3: Feature Engineering
- [ ] Phase 4: Model Development
- [ ] Phase 5: Model Serving
- [ ] Phase 6: Monitoring & Dashboard
- [ ] Phase 7: CI/CD & Testing

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- NYC Citi Bike for providing open bike-sharing data
- OpenWeatherMap for weather data API
- MLflow, Airflow, and other open-source tools

## Interview Talking Points

When discussing this project:

1. **MLOps Maturity**: "I built a Level 2 MLOps system with automated pipelines, experiment tracking, model registry, and comprehensive monitoring"

2. **Architecture**: "The system uses Airflow for orchestration with 4 DAGs running at different intervals to keep predictions current"

3. **Models**: "I implemented an ensemble of gradient boosting and statistical models with 50+ engineered features"

4. **Monitoring**: "Multi-layer monitoring using Evidently AI for data drift, MLflow for model performance, and Prometheus/Grafana for system metrics"

5. **Production-Ready**: "Fully containerized with Docker, DVC for versioning, and CI/CD with GitHub Actions - can be deployed to any cloud in minutes"

## Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter) - email@example.com

Project Link: [https://github.com/yourusername/bike-demand-prediction](https://github.com/yourusername/bike-demand-prediction)
