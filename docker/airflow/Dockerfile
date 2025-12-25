# Airflow Dockerfile
FROM apache/airflow:2.8.0-python3.11

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements
COPY pyproject.toml /tmp/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pandas>=2.1.0 \
    numpy>=1.25.0 \
    scikit-learn>=1.3.0 \
    xgboost>=2.0.0 \
    lightgbm>=4.1.0 \
    mlflow>=2.9.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.23 \
    requests>=2.31.0 \
    python-dotenv>=1.0.0 \
    pyyaml>=6.0.1 \
    loguru>=0.7.2 \
    great-expectations>=0.18.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0

# Set working directory
WORKDIR /opt/airflow
