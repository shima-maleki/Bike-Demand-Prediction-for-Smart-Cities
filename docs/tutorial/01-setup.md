# Chapter 1: Setup & Prerequisites

## Overview

In this chapter, you'll:
- Install all required tools
- Clone the project repository
- Understand the project structure
- Verify your environment is ready

**Estimated Time**: 1 hour

## Step 1: Install Docker Desktop

### Why Docker?
Docker packages your application with all its dependencies into "containers" - think of them as lightweight virtual machines. This ensures the system works identically on your laptop, your colleague's computer, and in production.

### Installation

**macOS:**
```bash
# Download from https://www.docker.com/products/docker-desktop/
# Install the .dmg file
# Start Docker Desktop from Applications
```

**Windows:**
```bash
# Download from https://www.docker.com/products/docker-desktop/
# Install the .exe file
# Important: Enable WSL 2 backend when prompted
# Start Docker Desktop
```

**Linux (Ubuntu/Debian):**
```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### Verify Installation
```bash
# Check Docker version
docker --version
# Should output: Docker version 24.x.x or higher

# Check Docker Compose
docker compose version
# Should output: Docker Compose version v2.x.x or higher

# Test Docker is running
docker run hello-world
# Should download and run a test container
```

**Troubleshooting:**
- **"Docker daemon not running"**: Start Docker Desktop
- **"Permission denied"**: Add user to docker group (Linux) or restart Docker Desktop
- **WSL error (Windows)**: Enable WSL 2 in Windows Features

## Step 2: Install Git

### Why Git?
Git is version control - it tracks changes to your code, allows collaboration, and enables reverting mistakes.

**macOS:**
```bash
# Install via Homebrew (recommended)
brew install git

# OR download from https://git-scm.com/download/mac
```

**Windows:**
```bash
# Download from https://git-scm.com/download/win
# Install with default options
# Use Git Bash for commands
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install git
```

### Configure Git
```bash
# Set your name and email (required for commits)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify
git config --list
```

## Step 3: Clone the Repository

```bash
# Navigate to your projects folder
cd ~/Documents  # or wherever you keep projects

# Clone the repository
git clone https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities.git

# Navigate into the project
cd Bike-Demand-Prediction-for-Smart-Cities

# Verify you're on the main branch
git branch
# Should show: * main
```

## Step 4: Understand the Project Structure

```
Bike-Demand-Prediction-for-Smart-Cities/
│
├── src/                          # Source code
│   ├── config/                   # Configuration management
│   │   ├── database.py          # Database connections
│   │   └── settings.py          # Application settings (Pydantic)
│   ├── data/                     # Data collection & processing
│   │   ├── collectors/          # API data collectors
│   │   │   ├── citi_bike_collector.py
│   │   │   └── weather_collector.py
│   │   ├── processors/          # Data validation & cleaning
│   │   └── storage/             # Database handlers
│   ├── features/                 # Feature engineering
│   │   ├── temporal_features.py # Hour, day, weekend, etc.
│   │   ├── lag_features.py      # 1h, 6h, 24h lags
│   │   ├── rolling_features.py  # Moving averages
│   │   ├── weather_features.py  # Weather enrichment
│   │   └── holiday_features.py  # Holiday detection
│   ├── models/                   # ML models
│   │   ├── base_model.py        # Abstract base class
│   │   ├── tree_models.py       # XGBoost, LightGBM
│   │   └── model_registry.py    # MLflow integration
│   ├── training/                 # Training pipeline
│   │   ├── train_pipeline.py    # Main training orchestrator
│   │   ├── evaluator.py         # Model evaluation
│   │   └── feature_store.py     # Feature retrieval
│   ├── serving/                  # Model serving
│   │   ├── api/                 # FastAPI application
│   │   │   ├── main.py          # API entry point
│   │   │   └── routers/         # API endpoints
│   │   ├── predictor.py         # Prediction logic
│   │   └── model_loader.py      # Load from MLflow
│   ├── monitoring/               # Observability
│   │   └── data_drift_detector.py
│   └── utils/                    # Shared utilities
│
├── airflow/                      # Workflow orchestration
│   └── dags/                    # DAG definitions
│       ├── data_ingestion_dag.py
│       ├── weather_enrichment_dag.py
│       ├── feature_engineering_dag.py
│       └── model_training_dag.py
│
├── dashboard/                    # Streamlit UI
│   ├── app.py                   # Main dashboard
│   └── pages/                   # Multi-page dashboard
│       ├── 1_demand_forecast.py
│       ├── 2_model_performance.py
│       ├── 3_data_quality.py
│       └── 4_system_health.py
│
├── docker/                       # Dockerfiles for each service
│   ├── api/Dockerfile           # FastAPI container
│   ├── dashboard/Dockerfile     # Streamlit container
│   ├── airflow/Dockerfile       # Airflow container
│   └── training/Dockerfile      # Training container
│
├── infrastructure/               # Infrastructure setup
│   ├── docker-compose.yml       # Multi-service orchestration
│   ├── postgres/
│   │   └── schema.sql           # Database schema
│   └── monitoring/
│       └── prometheus.yml
│
├── scripts/                      # Utility scripts
│   ├── backfill_historical_data.py
│   ├── backfill_weather.py
│   └── generate_features.py
│
├── tests/                        # Test suites
│   ├── unit/
│   └── integration/
│
├── .github/workflows/            # CI/CD pipelines
│   ├── ci.yml                   # Continuous Integration
│   ├── cd.yml                   # Continuous Deployment
│   └── model-training.yml       # Automated training
│
├── config/                       # Configuration files
│   ├── model_config.yml         # Model hyperparameters
│   └── feature_config.yml       # Feature definitions
│
├── docs/                         # Documentation
│   └── tutorial/                # This tutorial!
│
├── pyproject.toml                # Python dependencies
├── README.md                     # Quick start guide
└── .env.example                  # Environment variables template
```

### Key Directories Explained

| Directory | Purpose | When You'll Work Here |
|-----------|---------|----------------------|
| `src/` | All application code | Chapters 3-10 |
| `airflow/dags/` | Workflow definitions | Chapter 8 |
| `dashboard/` | UI components | Chapter 7 |
| `docker/` | Container definitions | All chapters |
| `infrastructure/` | Setup & config | Chapter 2 |
| `scripts/` | One-off utilities | Chapters 3-5 |
| `.github/workflows/` | CI/CD automation | Chapter 10 |

## Step 5: Install Python (Optional for Local Development)

While Docker handles all Python dependencies, you may want Python locally for IDE support and testing.

```bash
# Check if Python 3.11+ is installed
python3 --version

# If not, install Python 3.11
# macOS:
brew install python@3.11

# Windows: Download from https://www.python.org/downloads/
# Linux:
sudo apt-get install python3.11 python3.11-venv
```

### Create Virtual Environment (Optional)
```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Step 6: Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use any text editor
```

**Edit `.env` file:**
```bash
# Database Configuration
DB_HOST=bike_demand_postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_DATABASE=bike_demand_db

# MLflow Configuration
MLFLOW_TRACKING_URI=http://bike_demand_mlflow:5000

# API Keys (Optional - use defaults for tutorial)
WEATHER_API_KEY=your_openweathermap_key_here

# Environment
ENVIRONMENT=development
```

**Get Weather API Key (Optional):**
1. Go to [openweathermap.org](https://openweathermap.org/api)
2. Sign up for free account
3. Get API key from dashboard
4. Add to `.env` file

**Note**: The tutorial works with synthetic data, so API key is optional for learning.

## Step 7: Verify Docker Compose Setup

```bash
# Navigate to infrastructure directory
cd infrastructure

# Verify docker-compose.yml exists
ls -la docker-compose.yml

# Check the file (don't start yet!)
cat docker-compose.yml
```

You should see services defined:
- `postgres` - Database
- `mlflow` - Experiment tracking
- `airflow-webserver` - Workflow UI
- `airflow-scheduler` - Workflow executor
- `api` - FastAPI server
- `dashboard` - Streamlit UI

## Step 8: Test Your Setup

```bash
# Return to project root
cd ..

# Test Docker Compose configuration (doesn't start services)
docker compose -f infrastructure/docker-compose.yml config

# Should output the parsed configuration without errors
```

## Step 9: Install a Code Editor (Recommended)

### VS Code (Recommended)
```bash
# Download from https://code.visualstudio.com/

# Recommended extensions:
# - Python (Microsoft)
# - Docker (Microsoft)
# - YAML (Red Hat)
# - GitLens
# - GitHub Copilot (optional)
```

**Open project in VS Code:**
```bash
code .
```

## Summary Checklist

Before moving to Chapter 2, verify you have:

- [ ] Docker Desktop installed and running
- [ ] Docker version 24.x or higher
- [ ] Docker Compose version 2.x or higher
- [ ] Git installed and configured
- [ ] Repository cloned successfully
- [ ] `.env` file created from `.env.example`
- [ ] Code editor installed (VS Code recommended)
- [ ] Understand project structure

## Common Issues & Solutions

### Issue: Docker commands require sudo (Linux)
**Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Port conflicts (8000, 5000, 8080 already in use)
**Solution:**
```bash
# Find processes using ports
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Stop the conflicting service or change ports in docker-compose.yml
```

### Issue: Git clone fails with authentication error
**Solution:**
```bash
# Use HTTPS instead of SSH
git clone https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities.git
```

### Issue: Python version mismatch
**Solution:**
```bash
# Use Docker for everything - no local Python needed
# OR install Python 3.11 specifically:
brew install python@3.11  # macOS
```

## What You Learned

✅ **Docker**: Containerization basics, why we use it
✅ **Git**: Version control, cloning repositories
✅ **Project Structure**: Where everything lives
✅ **Environment Setup**: Configuration management
✅ **Development Tools**: Code editors, terminal commands

## Next Steps

Now that your environment is ready, head to **[Chapter 2: Database & Infrastructure](02-database.md)** to set up PostgreSQL and understand the data model.

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
