# Tutorial: Building a Production-Grade Bike Demand Forecasting System

## Welcome!

This tutorial will guide you through building a complete **Level 2 MLOps system** for predicting bike rental demand in smart cities. By the end, you'll have built a production-ready machine learning system that:

- 📊 Collects real-time data from NYC Citi Bike APIs
- 🌦️ Enriches data with weather information
- 🔧 Automatically engineers 22+ time-series features
- 🤖 Trains and evaluates multiple ML models (XGBoost, LightGBM)
- 📈 Tracks experiments and versions models with MLflow
- 🚀 Serves predictions via FastAPI
- 📊 Provides an interactive dashboard with Streamlit
- 🔄 Automates everything with Apache Airflow
- 🐳 Runs entirely in Docker containers
- ✅ Has CI/CD pipelines with GitHub Actions

## What You'll Build

### The Problem
Cities need to predict bike demand at different stations to:
- Rebalance bikes efficiently (move bikes from low-demand to high-demand stations)
- Optimize maintenance schedules
- Plan new station locations
- Improve user experience (ensure bikes are available when needed)

### The Solution
A complete MLOps system that:
1. **Ingests data** every 15 minutes from Citi Bike API
2. **Enriches** with weather data every 30 minutes
3. **Engineers features** hourly (temporal, lag, rolling, weather, holidays)
4. **Trains models** daily with automated evaluation
5. **Serves predictions** via REST API with <100ms latency
6. **Monitors** model performance, data quality, and system health
7. **Alerts** on data drift, model degradation, or system issues

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Sources                             │
├─────────────────────────────────────────────────────────────────┤
│  NYC Citi Bike API  │  OpenWeatherMap API  │  Holiday Calendar  │
└──────────┬──────────┴──────────┬───────────┴──────────┬─────────┘
           │                     │                       │
           ▼                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Apache Airflow (Orchestration)                │
├─────────────────────────────────────────────────────────────────┤
│  Data Ingestion DAG (15 min) → Feature Engineering DAG (1 hour) │
│  Weather Enrichment DAG (30 min) → Model Training DAG (daily)   │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
├─────────────────────────────────────────────────────────────────┤
│  bike_stations │ bike_station_status │ weather_data │ features  │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Training Pipeline                             │
├─────────────────────────────────────────────────────────────────┤
│  Feature Store → XGBoost/LightGBM Training → Evaluation         │
│                    → MLflow Tracking → Model Registry            │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MLflow Server                              │
├─────────────────────────────────────────────────────────────────┤
│  Experiment Tracking │ Model Registry (Staging/Production)      │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Server                               │
├─────────────────────────────────────────────────────────────────┤
│  /predict │ /predict/batch │ /forecast │ /health │ /metrics    │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                            │
├─────────────────────────────────────────────────────────────────┤
│  Demand Forecast │ Model Performance │ Data Quality │ Health    │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Why These Technologies?

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Docker** | Containerization | Ensures reproducibility, easy deployment anywhere |
| **PostgreSQL** | Database | Robust time-series data storage, JSONB for features |
| **Apache Airflow** | Orchestration | Industry-standard workflow automation, DAG-based |
| **MLflow** | Experiment Tracking | Best-in-class model versioning and registry |
| **FastAPI** | API Framework | High performance, auto-generated docs, async support |
| **Streamlit** | Dashboard | Rapid prototyping, Python-native, interactive |
| **XGBoost/LightGBM** | Models | State-of-the-art gradient boosting, great for tabular data |
| **GitHub Actions** | CI/CD | Integrated with GitHub, free for public repos |
| **Prometheus/Grafana** | Monitoring | Industry-standard observability stack |

## MLOps Maturity Level

This system achieves **Level 2 MLOps maturity** (Google's MLOps framework):

- **Level 0**: Manual process - No automation
- **Level 1**: ML pipeline automation - Training automated
- **Level 2**: CI/CD pipeline automation ← **This project**
  - ✅ Automated data pipelines
  - ✅ Automated feature engineering
  - ✅ Automated training and evaluation
  - ✅ Automated model deployment
  - ✅ Comprehensive monitoring
  - ✅ CI/CD for code and models

## What You'll Learn

### 1. Data Engineering
- Collecting data from REST APIs
- Handling time-series data properly
- Database schema design for ML
- Data validation with Great Expectations
- ETL pipeline design

### 2. Feature Engineering
- Temporal features (hour, day, seasonality)
- Lag features (1h, 6h, 24h lookback)
- Rolling statistics (moving averages)
- Weather signal integration
- Holiday detection

### 3. Machine Learning
- Time-series forecasting
- Gradient boosting models (XGBoost, LightGBM)
- Hyperparameter tuning with Optuna
- Model evaluation (RMSE, MAE, MAPE, R²)
- Model versioning and registry

### 4. MLOps
- Experiment tracking with MLflow
- Model deployment strategies
- API design for ML systems
- Monitoring and alerting
- A/B testing infrastructure

### 5. DevOps
- Docker and containerization
- Docker Compose for multi-service apps
- CI/CD with GitHub Actions
- Infrastructure as Code
- Security best practices

### 6. Software Engineering
- Clean code architecture
- Design patterns (Factory, Singleton)
- Configuration management
- Logging and debugging
- Testing (unit, integration)

## Prerequisites

### Required Knowledge (Beginner-Friendly)
- **Python Basics**: Variables, functions, classes, loops
- **Basic SQL**: SELECT, INSERT, CREATE TABLE
- **Command Line**: cd, ls, running commands
- **Basic Git**: clone, commit, push

### Optional (Helpful but not required)
- Docker concepts (we'll teach you)
- Machine learning basics (we'll explain)
- REST APIs (we'll show examples)

### Required Software
- **Docker Desktop** - Download from [docker.com](https://www.docker.com/products/docker-desktop/)
- **Git** - Download from [git-scm.com](https://git-scm.com/)
- **Text Editor** - VS Code (recommended) or any editor
- **Terminal** - Built-in terminal on Mac/Linux, WSL or PowerShell on Windows

### Recommended Hardware
- 8GB+ RAM (for Docker containers)
- 10GB+ free disk space
- Modern CPU (4+ cores recommended)

## Tutorial Structure

This tutorial is organized into phases, each building on the previous:

1. **[Introduction](00-introduction.md)** ← You are here
2. **[Setup & Prerequisites](01-setup.md)** - Install tools, clone repo, understand structure
3. **[Database & Infrastructure](02-database.md)** - PostgreSQL schema, Docker Compose
4. **[Data Collection Pipeline](03-data-collection.md)** - Fetch Citi Bike & weather data
5. **[Feature Engineering Pipeline](04-feature-engineering.md)** - Build 22+ features
6. **[Model Training Pipeline](05-model-training.md)** - Train XGBoost & LightGBM
7. **[Model Serving (API)](06-model-serving.md)** - FastAPI deployment
8. **[Dashboard Development](07-dashboard.md)** - Streamlit UI
9. **[Orchestration with Airflow](08-airflow.md)** - Automate everything
10. **[Monitoring & Observability](09-monitoring.md)** - Track performance
11. **[CI/CD Pipeline](10-cicd.md)** - GitHub Actions automation
12. **[Design Decisions](11-design-decisions.md)** - Why we made certain choices
13. **[Production Deployment](12-production.md)** - Deploy to cloud (AWS/GCP/Azure)
14. **[Troubleshooting Guide](13-troubleshooting.md)** - Common issues and solutions

## How to Use This Tutorial

### 🎯 For Complete Beginners
1. Read each chapter sequentially
2. Follow all steps, don't skip
3. Type commands yourself (don't copy-paste blindly)
4. Experiment with changing values
5. Ask questions in GitHub Issues

### 🚀 For Experienced Developers
1. Skim chapters 1-2 for setup
2. Focus on chapters 3-11 for implementation
3. Read chapter 12 for architectural insights
4. Jump to specific chapters as needed

### 💡 For Learners
- Each chapter has a "Key Concepts" section
- Code snippets are explained line-by-line
- "Why?" sections explain design decisions
- "Common Mistakes" highlight pitfalls
- Exercises at the end of each chapter

## Estimated Time

- **Full Tutorial (All Chapters)**: 20-30 hours
- **Quick Start (Chapters 1-3)**: 2-3 hours
- **Core ML Pipeline (Chapters 4-6)**: 8-10 hours
- **Deployment & Production (Chapters 7-11)**: 10-12 hours

## Support & Community

- **GitHub Issues**: Report bugs or ask questions
- **GitHub Discussions**: Share your builds, ask for advice
- **Pull Requests**: Improve the tutorial, fix typos

## Learning Path

```
START HERE
    │
    ├─► Chapter 1: Setup (1 hour)
    │       │
    │       └─► ✅ Docker installed, repo cloned
    │
    ├─► Chapter 2: Database (2 hours)
    │       │
    │       └─► ✅ PostgreSQL running, schema created
    │
    ├─► Chapter 3: Data Collection (3 hours)
    │       │
    │       └─► ✅ Data flowing from APIs to database
    │
    ├─► Chapter 4: Features (4 hours)
    │       │
    │       └─► ✅ 22+ features engineered
    │
    ├─► Chapter 5: Training (5 hours)
    │       │
    │       └─► ✅ Models trained, MLflow tracking
    │
    ├─► Chapter 6: API (3 hours)
    │       │
    │       └─► ✅ FastAPI serving predictions
    │
    ├─► Chapter 7: Dashboard (3 hours)
    │       │
    │       └─► ✅ Streamlit UI working
    │
    ├─► Chapter 8: Airflow (3 hours)
    │       │
    │       └─► ✅ Automated pipelines
    │
    ├─► Chapter 9: Monitoring (2 hours)
    │       │
    │       └─► ✅ Metrics, alerts, dashboards
    │
    ├─► Chapter 10: CI/CD (2 hours)
    │       │
    │       └─► ✅ GitHub Actions automated
    │
    └─► DONE! 🎉
            │
            └─► Production-ready MLOps system!
```

## Next Steps

Ready to start? Head to **[Chapter 1: Setup & Prerequisites](01-setup.md)** to begin building!

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)

**Want to contribute?** Check our [Contributing Guide](../../CONTRIBUTING.md)
