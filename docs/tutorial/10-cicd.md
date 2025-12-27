# Chapter 10: CI/CD Pipeline

## Overview

This chapter guides you through implementing continuous integration and deployment (CI/CD) pipelines using GitHub Actions to automate testing, Docker builds, and deployments.

**What You'll Build**:
- Automated testing on every commit (linting, unit tests, integration tests)
- Docker image builds and pushes to registry
- Automated model training pipeline
- Deployment automation
- Code quality checks (coverage, security scans)

**Estimated Time**: 2-3 hours

## Why CI/CD?

**The Problem**: Manual testing and deployment is:
- **Error-prone**: Humans forget steps
- **Slow**: 30+ minutes per deployment
- **Inconsistent**: Works on my machine, fails in production
- **Risky**: No automated rollback

**With CI/CD**:
- **Automated Testing**: Every commit tested in <5 minutes
- **Consistent Builds**: Same Docker images in dev/staging/prod
- **Fast Feedback**: Know within minutes if code breaks
- **Safe Deployments**: Automated rollback on failure

---

## Architecture

```
GitHub Push
    ↓
┌──────────────────────────────────────────┐
│  CI Workflow (on every push/PR)         │
│  ├─ Lint (black, flake8, mypy)          │
│  ├─ Unit Tests (pytest)                 │
│  ├─ Integration Tests                    │
│  ├─ Coverage Report (>80% required)     │
│  └─ Security Scan (bandit, safety)      │
└──────────────────────────────────────────┘
    ↓ (if main branch)
┌──────────────────────────────────────────┐
│  CD Workflow (on main branch)           │
│  ├─ Build Docker Images                 │
│  ├─ Tag (SHA + latest)                  │
│  ├─ Push to Docker Hub / GCR            │
│  └─ Deploy to Staging (optional)        │
└──────────────────────────────────────────┘
    ↓ (weekly schedule)
┌──────────────────────────────────────────┐
│  Model Training Workflow (weekly)       │
│  ├─ Trigger Airflow training DAG        │
│  ├─ Wait for completion                 │
│  ├─ Validate model RMSE < 1.0           │
│  └─ Promote to production               │
└──────────────────────────────────────────┘
```

---

## Step 1: Continuous Integration (CI)

### `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    name: Code Quality Checks
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install black flake8 mypy bandit safety
          pip install -e .

      - name: Run Black (code formatting)
        run: black --check src/ tests/

      - name: Run Flake8 (linting)
        run: flake8 src/ tests/ --max-line-length=120 --ignore=E203,W503

      - name: Run MyPy (type checking)
        run: mypy src/ --ignore-missing-imports

      - name: Run Bandit (security scan)
        run: bandit -r src/ -ll

      - name: Check dependencies for vulnerabilities
        run: safety check --json

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov pytest-mock
          pip install -e .

      - name: Run unit tests
        run: |
          pytest tests/unit/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: bike_demand_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          pip install -e .

      - name: Wait for PostgreSQL
        run: |
          until pg_isready -h localhost -p 5432; do
            echo "Waiting for postgres..."
            sleep 2
          done

      - name: Initialize database
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_NAME: bike_demand_test
          DB_USER: postgres
          DB_PASSWORD: postgres
        run: |
          psql -h localhost -U postgres -d bike_demand_test -f infrastructure/postgres/schema.sql

      - name: Run integration tests
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_NAME: bike_demand_test
          DB_USER: postgres
          DB_PASSWORD: postgres
        run: |
          pytest tests/integration/ -v

  docker-build-test:
    name: Test Docker Builds
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build API Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api/Dockerfile
          push: false
          tags: bike-demand-api:test

      - name: Build Dashboard Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/dashboard/Dockerfile
          push: false
          tags: bike-demand-dashboard:test
```

**Key Features**:
- **Parallel Jobs**: Lint, unit tests, integration tests run concurrently
- **PostgreSQL Service**: Spins up test database for integration tests
- **Coverage Requirement**: Tests must maintain >80% coverage
- **Security Scanning**: Bandit checks for security issues, Safety checks dependencies
- **Docker Build Test**: Ensures Dockerfiles are valid

---

## Step 2: Continuous Deployment (CD)

### `.github/workflows/cd.yml`

```yaml
name: CD Pipeline

on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Allow manual trigger

env:
  DOCKER_REGISTRY: docker.io
  DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}

jobs:
  build-and-push:
    name: Build and Push Docker Images
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract Git metadata
        id: meta
        run: |
          echo "sha_short=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT
          echo "build_date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> $GITHUB_OUTPUT

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-api:latest
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-api:${{ steps.meta.outputs.sha_short }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/bike-demand-api:latest
          cache-to: type=inline

      - name: Build and push Dashboard image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/dashboard/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-dashboard:latest
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-dashboard:${{ steps.meta.outputs.sha_short }}

      - name: Build and push Airflow image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/airflow/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-airflow:latest
            ${{ secrets.DOCKER_USERNAME }}/bike-demand-airflow:${{ steps.meta.outputs.sha_short }}

      - name: Image digest
        run: echo "Images pushed with tags latest and ${{ steps.meta.outputs.sha_short }}"

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to staging server via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/bike-demand-prediction
            git pull origin main
            docker-compose pull
            docker-compose up -d
            docker system prune -f

      - name: Wait for services to start
        run: sleep 30

      - name: Run smoke tests
        run: |
          # Test API health
          curl -f http://${{ secrets.STAGING_HOST }}:8000/health || exit 1

          # Test prediction endpoint
          curl -X POST http://${{ secrets.STAGING_HOST }}:8000/predict \
            -H "Content-Type: application/json" \
            -d '{"station_id": "test-station"}' || exit 1

      - name: Rollback on failure
        if: failure()
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/bike-demand-prediction
            docker-compose down
            git reset --hard HEAD~1
            docker-compose up -d
```

**Key Features**:
- **Docker Layer Caching**: Speeds up builds by reusing layers
- **Multi-tagging**: Images tagged with both `latest` and Git SHA
- **Automated Deployment**: Pushes to staging on main branch
- **Smoke Tests**: Verifies deployment before marking as successful
- **Automated Rollback**: Reverts to previous version on failure

### GitHub Secrets Setup

Add these secrets in **Settings → Secrets → Actions**:

- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub access token
- `STAGING_HOST` - Staging server IP/hostname
- `STAGING_USER` - SSH username
- `STAGING_SSH_KEY` - Private SSH key for server access

---

## Step 3: Model Training Pipeline

### `.github/workflows/model-training.yml`

```yaml
name: Automated Model Training

on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  train-model:
    name: Train and Evaluate Model
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Trigger Airflow DAG via API
        env:
          AIRFLOW_HOST: ${{ secrets.AIRFLOW_HOST }}
          AIRFLOW_USERNAME: ${{ secrets.AIRFLOW_USERNAME }}
          AIRFLOW_PASSWORD: ${{ secrets.AIRFLOW_PASSWORD }}
        run: |
          # Trigger model training DAG
          curl -X POST \
            "http://${AIRFLOW_HOST}/api/v1/dags/model_training/dagRuns" \
            -H "Content-Type: application/json" \
            -u "${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD}" \
            -d '{}'

      - name: Wait for DAG completion
        env:
          AIRFLOW_HOST: ${{ secrets.AIRFLOW_HOST }}
          AIRFLOW_USERNAME: ${{ secrets.AIRFLOW_USERNAME }}
          AIRFLOW_PASSWORD: ${{ secrets.AIRFLOW_PASSWORD }}
        run: |
          # Poll DAG run status
          for i in {1..60}; do
            STATUS=$(curl -s \
              "http://${AIRFLOW_HOST}/api/v1/dags/model_training/dagRuns" \
              -u "${AIRFLOW_USERNAME}:${AIRFLOW_PASSWORD}" \
              | jq -r '.dag_runs[0].state')

            echo "DAG status: $STATUS"

            if [ "$STATUS" == "success" ]; then
              echo "✅ Training completed successfully"
              exit 0
            elif [ "$STATUS" == "failed" ]; then
              echo "❌ Training failed"
              exit 1
            fi

            sleep 30
          done

          echo "⏰ Timeout waiting for training"
          exit 1

      - name: Validate model performance
        env:
          MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
        run: |
          python scripts/validate_model.py --rmse-threshold 1.0

      - name: Notify on Slack
        if: always()
        uses: slackapi/slack-github-action@v1.24.0
        with:
          payload: |
            {
              "text": "Model Training ${{ job.status }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Model Training Result:* ${{ job.status }}\n*Triggered by:* ${{ github.actor }}\n*Commit:* ${{ github.sha }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Model Validation Script

Create `scripts/validate_model.py`:

```python
"""
Validate that newly trained model meets performance criteria
"""

import mlflow
import argparse
import sys
from mlflow.tracking import MlflowClient

def validate_model(rmse_threshold: float = 1.0):
    """
    Check if latest model version meets performance threshold

    Args:
        rmse_threshold: Maximum acceptable RMSE

    Returns:
        0 if valid, 1 if validation fails
    """
    client = MlflowClient()

    # Get latest Production model
    model_name = "bike-demand-forecaster"

    try:
        versions = client.get_latest_versions(model_name, stages=["Production"])

        if not versions:
            print("❌ No model in Production stage")
            return 1

        latest_version = versions[0]

        # Get metrics
        run = client.get_run(latest_version.run_id)
        metrics = run.data.metrics

        rmse = metrics.get('rmse', float('inf'))

        print(f"Model version: {latest_version.version}")
        print(f"RMSE: {rmse:.3f}")
        print(f"Threshold: {rmse_threshold}")

        if rmse <= rmse_threshold:
            print(f"✅ Model validation passed (RMSE={rmse:.3f} <= {rmse_threshold})")
            return 0
        else:
            print(f"❌ Model validation failed (RMSE={rmse:.3f} > {rmse_threshold})")
            return 1

    except Exception as e:
        print(f"❌ Error validating model: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--rmse-threshold', type=float, default=1.0)
    args = parser.parse_args()

    exit_code = validate_model(rmse_threshold=args.rmse_threshold)
    sys.exit(exit_code)
```

---

## Step 4: Pre-commit Hooks

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120', '--ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
        args: ['--ignore-missing-imports']
```

### Setup Pre-commit

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files (first time)
pre-commit run --all-files
```

Now, linting runs automatically before every commit!

---

## Step 5: Testing Infrastructure

### Unit Tests

Create `tests/unit/test_collectors.py`:

```python
"""
Unit tests for data collectors
"""

import pytest
from unittest.mock import Mock, patch
from src.data.collectors.citi_bike_collector import CitiBikeCollector

class TestCitiBikeCollector:
    def test_fetch_station_status_success(self):
        """Test successful API call"""

        collector = CitiBikeCollector()

        # Mock requests.get
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': {
                    'stations': [
                        {
                            'station_id': 'test-1',
                            'num_bikes_available': 5,
                            'num_docks_available': 15
                        }
                    ]
                }
            }
            mock_get.return_value = mock_response

            result = collector.fetch_station_status()

            assert len(result) == 1
            assert result[0]['station_id'] == 'test-1'
            assert result[0]['num_bikes_available'] == 5

    def test_fetch_station_status_api_error(self):
        """Test API error handling"""

        collector = CitiBikeCollector()

        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("API Down")

            with pytest.raises(Exception):
                collector.fetch_station_status()
```

### Integration Tests

Create `tests/integration/test_data_pipeline.py`:

```python
"""
Integration test for data ingestion pipeline
"""

import pytest
import psycopg2
from src.data.collectors.citi_bike_collector import CitiBikeCollector
from src.data.storage.postgres_handler import PostgresHandler
import os

@pytest.fixture
def db_connection():
    """Create test database connection"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'bike_demand_test'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )
    yield conn
    conn.close()

def test_end_to_end_data_ingestion(db_connection):
    """Test complete flow: API → Database"""

    # 1. Fetch from API
    collector = CitiBikeCollector()
    stations = collector.fetch_station_status()

    assert len(stations) > 0

    # 2. Insert to database
    handler = PostgresHandler(db_connection)
    handler.insert_station_status(stations[:10])  # Insert first 10

    # 3. Verify in database
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM bike_station_status")
    count = cursor.fetchone()[0]

    assert count == 10
```

---

## Step 6: Deployment Strategies

### Blue-Green Deployment

```yaml
# docker-compose.blue-green.yml

services:
  api-blue:
    image: ${DOCKER_USERNAME}/bike-demand-api:${BLUE_TAG}
    container_name: api-blue
    environment:
      - ENV=blue
    networks:
      - bike-demand-network

  api-green:
    image: ${DOCKER_USERNAME}/bike-demand-api:${GREEN_TAG}
    container_name: api-green
    environment:
      - ENV=green
    networks:
      - bike-demand-network

  nginx:
    image: nginx:latest
    ports:
      - "8000:80"
    volumes:
      - ./nginx-blue-green.conf:/etc/nginx/nginx.conf
    depends_on:
      - api-blue
      - api-green
    networks:
      - bike-demand-network
```

Switch traffic:

```bash
# Deploy new version to green
export GREEN_TAG=abc123
docker-compose -f docker-compose.blue-green.yml up -d api-green

# Test green
curl http://localhost:8000/health

# Switch traffic (update nginx config to point to green)
# Rollback: switch nginx back to blue
```

### Canary Deployment

Use Nginx to route 10% traffic to new version:

```nginx
upstream backend {
    server api-stable:8000 weight=9;
    server api-canary:8000 weight=1;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
    }
}
```

---

## Step 7: Monitoring CI/CD

### GitHub Actions Dashboard

View workflow runs:
- **Actions** tab in GitHub
- Filter by workflow, status, branch
- View logs for each job/step

### Status Badges

Add to `README.md`:

```markdown
![CI](https://github.com/your-username/Bike-Demand-Prediction-for-Smart-Cities/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/your-username/Bike-Demand-Prediction-for-Smart-Cities/actions/workflows/cd.yml/badge.svg)
[![codecov](https://codecov.io/gh/your-username/Bike-Demand-Prediction-for-Smart-Cities/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/Bike-Demand-Prediction-for-Smart-Cities)
```

### Slack Notifications

Add to workflows:

```yaml
- name: Notify Slack on Failure
  if: failure()
  uses: slackapi/slack-github-action@v1.24.0
  with:
    payload: |
      {
        "text": "🚨 CI Failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Workflow:* ${{ github.workflow }}\n*Status:* Failed\n*Branch:* ${{ github.ref }}\n*Commit:* ${{ github.sha }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Common Issues & Fixes

### Issue: "Docker build fails in CI"

**Cause**: Missing dependencies in Dockerfile

**Fix**:
```dockerfile
# Add to Dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

Test locally:
```bash
docker build -t test-image -f docker/api/Dockerfile .
```

### Issue: "Tests pass locally but fail in CI"

**Cause**: Environment differences (Python version, dependencies)

**Fix**: Use same Python version in CI as local:
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'  # Match your local version
```

### Issue: "Deployment hangs"

**Cause**: SSH connection timeout

**Fix**: Add timeout and better logging:
```yaml
- name: Deploy
  timeout-minutes: 10
  run: |
    ssh -o ConnectTimeout=30 user@host "docker-compose up -d"
```

### Issue: "Coverage drops below threshold"

**Cause**: New code not covered by tests

**Fix**: Add tests or adjust threshold:
```bash
pytest --cov-fail-under=75  # Lower threshold temporarily
```

---

## Interview Talking Points

1. **"I implemented a comprehensive CI/CD pipeline with GitHub Actions covering linting, testing, Docker builds, and automated deployments"**

2. **"The CI pipeline runs unit tests, integration tests with PostgreSQL, security scans with Bandit, and enforces 80% code coverage"**

3. **"I automated model training on a weekly schedule using GitHub Actions to trigger Airflow DAGs, validate performance, and promote to production"**

4. **"The deployment pipeline uses blue-green strategy with automated smoke tests and rollback on failure to ensure zero-downtime deployments"**

5. **"I integrated Slack notifications for pipeline failures and Codecov for tracking test coverage trends over time"**

---

## Summary

You've built a production-grade CI/CD system:

✅ **Automated Testing** - Linting, unit tests, integration tests on every commit
✅ **Code Quality** - Black, Flake8, MyPy, 80% coverage requirement
✅ **Security Scanning** - Bandit, Safety dependency checks
✅ **Docker Automation** - Build, tag, push to registry on main branch
✅ **Deployment Automation** - SSH deploy to staging with smoke tests
✅ **Model Training Pipeline** - Weekly automated training via Airflow
✅ **Pre-commit Hooks** - Catch issues before commit
✅ **Rollback Strategy** - Automated rollback on deployment failure
✅ **Monitoring** - Status badges, Slack notifications

**What's Next?**

You've completed the full tutorial! You now have:
- End-to-end ML pipeline (data → features → training → serving)
- Production deployment with Docker Compose
- Comprehensive monitoring (drift, performance, system metrics)
- Automated CI/CD with GitHub Actions

**Recommended Next Steps**:
1. Deploy to cloud (AWS, GCP, Azure) using Chapter 12
2. Add A/B testing for model comparison
3. Implement real-time streaming with Kafka
4. Add SHAP for model explainability
5. Expand to multiple cities (SF, Chicago)

**Congratulations!** 🎉 You've built a professional MLOps system worthy of production deployment and portfolio showcase.

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)

**Explore More**:
- [Design Decisions](11-design-decisions.md) - Architecture rationale
- [Production Deployment](12-production.md) - Cloud deployment guide
- [Troubleshooting](13-troubleshooting.md) - Common issues and solutions
