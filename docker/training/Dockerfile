# Model Training Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pandas>=2.1.0 \
    numpy>=1.25.0 \
    scikit-learn>=1.3.0 \
    xgboost>=2.0.0 \
    lightgbm>=4.1.0 \
    catboost>=1.2.0 \
    prophet>=1.1.5 \
    statsmodels>=0.14.0 \
    tensorflow>=2.15.0 \
    mlflow>=2.9.0 \
    dvc>=3.30.0 \
    optuna>=3.5.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.23 \
    python-dotenv>=1.0.0 \
    pyyaml>=6.0.1 \
    loguru>=0.7.2 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models

# Default command
CMD ["python", "-m", "src.training.trainer"]
