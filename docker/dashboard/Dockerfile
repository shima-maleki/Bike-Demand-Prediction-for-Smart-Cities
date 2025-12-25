# Streamlit Dashboard Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pandas>=2.1.0 \
    numpy>=1.25.0 \
    streamlit>=1.29.0 \
    plotly>=5.18.0 \
    matplotlib>=3.8.0 \
    seaborn>=0.13.0 \
    psycopg2-binary>=2.9.9 \
    sqlalchemy>=2.0.23 \
    requests>=2.31.0 \
    python-dotenv>=1.0.0 \
    loguru>=0.7.2 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0

# Copy application code
COPY dashboard/ /app/dashboard/
COPY src/ /app/src/
COPY config/ /app/config/

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "dashboard/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
