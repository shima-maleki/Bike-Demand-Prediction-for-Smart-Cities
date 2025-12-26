# FastAPI Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
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
    mlflow>=2.9.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.23 \
    fastapi>=0.108.0 \
    uvicorn[standard]>=0.25.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    python-dotenv>=1.0.0 \
    loguru>=0.7.2 \
    prometheus-client>=0.19.0 \
    prometheus-fastapi-instrumentator>=6.1.0 \
    slowapi>=0.1.9 \
    python-multipart>=0.0.6 \
    holidays>=0.38

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/

# Create logs directory
RUN mkdir -p /app/logs

# Create mlflow directory and symlink for artifact compatibility
RUN mkdir -p /mlflow && ln -sf /mlflow/backend /mlflow/artifacts

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.serving.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
