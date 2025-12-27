# Chapters 3-10: Coming Soon

The following chapters are currently being developed. The complete implementation code is available in the repository, and you can follow along using the codebase.

## Chapter 3: Data Collection Pipeline
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Fetch data from NYC Citi Bike API
- Collect weather data from OpenWeatherMap
- Store data in PostgreSQL
- Validate data quality

**Reference code**: `src/data/collectors/`, `scripts/backfill_historical_data.py`

---

## Chapter 4: Feature Engineering Pipeline
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Temporal features (hour, day, weekend, rush hours)
- Lag features (1h, 6h, 24h lookback)
- Rolling statistics (moving averages, standard deviation)
- Weather enrichment
- Holiday detection

**Reference code**: `src/features/`, `scripts/generate_features.py`

---

## Chapter 5: Model Training Pipeline
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Train XGBoost and LightGBM models
- Hyperparameter tuning with Optuna
- Model evaluation metrics (RMSE, MAE, MAPE, R²)
- MLflow experiment tracking
- Model registry and versioning

**Reference code**: `src/training/`, `src/models/`

---

## Chapter 6: Model Serving (API)
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Build FastAPI server
- Implement prediction endpoints
- Batch predictions
- Health checks and monitoring
- Model loading from MLflow

**Reference code**: `src/serving/api/`

---

## Chapter 7: Dashboard Development
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Build Streamlit multi-page app
- Real-time demand forecasts
- Model performance visualization
- Data quality monitoring
- System health dashboard

**Reference code**: `dashboard/`

---

## Chapter 8: Orchestration with Airflow
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Setup Apache Airflow
- Create data ingestion DAG (every 15 min)
- Create feature engineering DAG (hourly)
- Create model training DAG (daily)
- Monitor and manage workflows

**Reference code**: `airflow/dags/`

---

## Chapter 9: Monitoring & Observability
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- Data drift detection with Evidently AI
- Model performance tracking
- System metrics with Prometheus
- Alerting setup
- Dashboard integration

**Reference code**: `src/monitoring/`

---

## Chapter 10: CI/CD Pipeline
**Status**: Code complete, tutorial in progress

**What you'll learn:**
- GitHub Actions workflows
- Automated testing (linting, unit tests)
- Docker image builds
- Deployment automation
- Model training in CI

**Reference code**: `.github/workflows/`

---

## Chapter 12: Production Deployment
**Status**: Tutorial in progress

**What you'll learn:**
- Deploy to AWS/GCP/Azure
- Kubernetes migration
- Security best practices
- Cost optimization
- Scaling strategies

---

## In the Meantime

While these chapters are being written, you can:

1. **Explore the codebase** - All code is documented with comments
2. **Read the main README** - Quick start guide available
3. **Check existing chapters**:
   - [Chapter 0: Introduction](00-introduction.md)
   - [Chapter 1: Setup](01-setup.md)
   - [Chapter 2: Database](02-database.md)
   - [Chapter 11: Design Decisions](11-design-decisions.md)
   - [Chapter 13: Troubleshooting](13-troubleshooting.md)

4. **Run the system** - Follow the Quick Start in the main README

5. **Contribute** - Help us write these chapters! Pull requests welcome.

---

**Want to be notified when new chapters are published?**
- ⭐ Star the repository
- 👀 Watch for updates
- 📬 Follow the project on GitHub

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
