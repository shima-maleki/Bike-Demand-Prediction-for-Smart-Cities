# Bike Demand Forecasting System - Complete Tutorial

## Welcome!

This comprehensive tutorial guides you through building a production-grade **Level 2 MLOps system** for predicting bike rental demand in smart cities. Whether you're a beginner or experienced developer, you'll learn to build a complete ML system from scratch.

## What You'll Build

A full-stack machine learning system featuring:
- 📊 Real-time data collection from NYC Citi Bike & Weather APIs
- 🔧 Automated feature engineering (22+ time-series features)
- 🤖 ML models (XGBoost, LightGBM) with experiment tracking
- 🚀 Production API with FastAPI (<100ms latency)
- 📈 Interactive dashboard with Streamlit
- 🔄 Automated pipelines with Apache Airflow
- 🐳 100% Docker-based deployment
- ✅ CI/CD with GitHub Actions

## Tutorial Structure

### Getting Started
1. **[Introduction](00-introduction.md)** (15 min)
   - What you'll build
   - System architecture
   - Technology stack
   - Prerequisites

2. **[Setup & Prerequisites](01-setup.md)** (1 hour)
   - Install Docker, Git, Python
   - Clone repository
   - Understand project structure
   - Verify environment

3. **[Database & Infrastructure](02-database.md)** (2 hours)
   - PostgreSQL schema design
   - Docker Compose orchestration
   - Create tables and indexes
   - Test database connectivity

### Core ML Pipeline
4. **[Data Collection Pipeline](03-data-collection.md)** (3 hours)
   - Fetch Citi Bike data from API
   - Collect weather data
   - Store in PostgreSQL
   - Data validation

5. **[Feature Engineering Pipeline](04-feature-engineering.md)** (4 hours)
   - Temporal features (hour, day, season)
   - Lag features (1h, 6h, 24h)
   - Rolling statistics (moving averages)
   - Weather & holiday features

6. **[Model Training Pipeline](05-model-training.md)** (5 hours)
   - Train XGBoost & LightGBM
   - Hyperparameter tuning with Optuna
   - Model evaluation (RMSE, MAE, R²)
   - MLflow experiment tracking

### Deployment & Production
7. **[Model Serving (API)](06-model-serving.md)** (3 hours)
   - FastAPI server setup
   - Prediction endpoints
   - Batch predictions
   - Health checks & monitoring

8. **[Dashboard Development](07-dashboard.md)** (3 hours)
   - Streamlit multi-page app
   - Real-time forecasts
   - Model performance charts
   - System health monitoring

9. **[Orchestration with Airflow](08-airflow.md)** (3 hours)
   - Setup Airflow
   - Data ingestion DAG (15 min)
   - Feature engineering DAG (hourly)
   - Model training DAG (daily)

### Production Operations
10. **[Monitoring & Observability](09-monitoring.md)** (2 hours)
    - Data drift detection (Evidently AI)
    - Model performance tracking
    - System metrics (Prometheus)
    - Alerting setup

11. **[CI/CD Pipeline](10-cicd.md)** (2 hours)
    - GitHub Actions workflows
    - Automated testing
    - Docker image builds
    - Deployment automation

### Advanced Topics
12. **[Design Decisions](11-design-decisions.md)** (1 hour)
    - Why PostgreSQL over TimescaleDB?
    - Why XGBoost over deep learning?
    - Why Airflow over Prefect?
    - Architectural trade-offs

13. **[Production Deployment](12-production.md)** (2 hours)
    - Deploy to AWS/GCP/Azure
    - Kubernetes migration
    - Security best practices
    - Cost optimization

14. **[Troubleshooting Guide](13-troubleshooting.md)** (Reference)
    - Common errors and solutions
    - Debugging techniques
    - Performance optimization
    - FAQ

## Learning Paths

### 🎯 For Complete Beginners (30 hours)
Follow chapters 1-13 sequentially. Don't skip any steps!

```
Week 1: Chapters 1-3 (Setup + Database)
Week 2: Chapters 4-6 (Data + Features + Training)
Week 3: Chapters 7-9 (API + Dashboard + Airflow)
Week 4: Chapters 10-13 (CI/CD + Production)
```

### 🚀 For Experienced Developers (15 hours)
Focus on ML and MLOps specifics:

```
Day 1: Chapters 1-2 (Skim setup)
Day 2: Chapters 4-6 (Feature engineering + Training)
Day 3: Chapters 7-9 (Deployment + Orchestration)
Day 4: Chapters 10-12 (CI/CD + Design decisions)
```

### 💼 For Interviews (5 hours)
Understand the system deeply:

```
1. Read: Chapter 00 (Architecture overview)
2. Skim: Chapters 4-6 (ML pipeline)
3. Deep dive: Chapter 11 (Design decisions)
4. Practice: Explain the system out loud
```

## Prerequisites

### Required Knowledge
- **Python Basics**: Functions, classes, loops, imports
- **SQL Basics**: SELECT, INSERT, JOIN
- **Command Line**: cd, ls, running commands
- **Git Basics**: clone, commit, push

### Optional (Helpful)
- Docker concepts
- Machine learning basics
- REST APIs
- Time-series analysis

### Required Software
- **Docker Desktop** (Required) - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/)
- **Text Editor** - VS Code recommended
- **8GB+ RAM**, 10GB+ disk space

## Quick Start (Skip the Tutorial)

If you just want to run the system:

```bash
# Clone repository
git clone https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities.git
cd Bike-Demand-Prediction-for-Smart-Cities

# Copy environment file
cp .env.example .env

# Start all services
cd infrastructure
docker compose up -d

# Wait for services to start (2-3 minutes)
docker compose ps

# Initialize database
docker compose exec -T postgres psql -U postgres -d bike_demand_db < postgres/schema.sql

# Load historical data
cd ..
docker compose -f infrastructure/docker-compose.yml run --rm -e PYTHONPATH=/app api python scripts/backfill_historical_data.py

# Train models
docker build -t bike-demand-trainer:latest -f docker/training/Dockerfile .
docker run --rm --network infrastructure_bike_demand_network \
  -e DB_HOST=bike_demand_postgres \
  -e DB_DATABASE=bike_demand_db \
  -e MLFLOW_TRACKING_URI=http://bike_demand_mlflow:5000 \
  bike-demand-trainer:latest

# Access services
# Dashboard: http://localhost:8501
# API: http://localhost:8000
# MLflow: http://localhost:5000
# Airflow: http://localhost:8080
```

## Tutorial Features

### For Learners
- ✅ **Step-by-step instructions** with explanations
- ✅ **"Why?" sections** explaining design decisions
- ✅ **Common mistakes** highlighted
- ✅ **Exercises** at end of chapters (coming soon)
- ✅ **Code snippets** with line-by-line explanations

### For Instructors
- ✅ **Modular chapters** - Assign specific sections
- ✅ **Estimated times** - Plan lessons
- ✅ **Prerequisites clearly marked**
- ✅ **Assessment questions** (coming soon)

### For Interview Prep
- ✅ **Talking points** for each chapter
- ✅ **Trade-off discussions**
- ✅ **Architectural diagrams**
- ✅ **Performance benchmarks**

## Key Concepts Covered

### Data Engineering
- Time-series data modeling
- ETL pipeline design
- Data validation (Great Expectations)
- API integration
- Database schema design

### Machine Learning
- Feature engineering for time-series
- Gradient boosting (XGBoost, LightGBM)
- Hyperparameter tuning (Optuna)
- Model evaluation metrics
- Avoiding data leakage

### MLOps
- Experiment tracking (MLflow)
- Model versioning and registry
- Automated pipelines (Airflow)
- Model serving (FastAPI)
- Monitoring and drift detection

### DevOps
- Docker and containerization
- Docker Compose orchestration
- CI/CD with GitHub Actions
- Infrastructure as Code
- Security best practices

## Expected Results

After completing this tutorial, you'll have:

- ✅ **Working MLOps system** running locally
- ✅ **Models achieving RMSE < 0.6** bikes
- ✅ **API latency < 100ms** for predictions
- ✅ **Automated pipelines** running on schedule
- ✅ **Interactive dashboard** with 4 pages
- ✅ **CI/CD pipelines** with 3 workflows
- ✅ **Complete documentation** for your portfolio

## Portfolio Impact

This project demonstrates:

1. **End-to-end ML system design**
2. **Production-grade code quality**
3. **DevOps and deployment expertise**
4. **Real-world data engineering**
5. **System architecture thinking**

**Interview Value: Very High** - Shows you can build complete systems, not just models.

## Success Metrics

Track your progress:

- [ ] Chapter 1: Environment set up
- [ ] Chapter 2: Database running
- [ ] Chapter 3: Data flowing from APIs
- [ ] Chapter 4: Features engineered
- [ ] Chapter 5: Models trained (RMSE < 0.6)
- [ ] Chapter 6: API serving predictions
- [ ] Chapter 7: Dashboard showing forecasts
- [ ] Chapter 8: Airflow DAGs running
- [ ] Chapter 9: Monitoring enabled
- [ ] Chapter 10: CI/CD automated
- [ ] Chapter 11: Understand all design decisions
- [ ] Chapter 12: Deployed to cloud (optional)

## Support & Community

- **GitHub Issues**: [Report bugs](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/discussions)
- **Pull Requests**: Improve the tutorial!

## Contributing

Found a typo? Have a suggestion? Contributions welcome!

1. Fork the repository
2. Create a branch (`git checkout -b improve-tutorial`)
3. Make changes
4. Submit Pull Request

## License

This tutorial and all code is licensed under Apache License 2.0.

## Acknowledgments

- NYC Citi Bike for open bike-sharing data
- Open-Meteo for free weather API
- MLflow, Airflow, FastAPI, Streamlit communities

---

## Start Learning!

Ready to begin? Head to **[Chapter 0: Introduction](00-introduction.md)** to start your journey!

**Estimated completion time**: 20-30 hours for full tutorial

**Questions?** Open an [issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
