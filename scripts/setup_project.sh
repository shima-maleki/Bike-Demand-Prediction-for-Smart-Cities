#!/bin/bash
# Project Setup Script
# Quick setup for the bike demand prediction project

set -e

echo "========================================="
echo "Bike Demand Prediction - Project Setup"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.11+ is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version detected"

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker detected"

# Check Docker Compose
echo "Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi
echo "✓ Docker Compose detected"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "IMPORTANT: Edit .env and add your OpenWeatherMap API key!"
    echo "Get a free key from: https://openweathermap.org/api"
    read -p "Press Enter to continue after you've added your API key..."
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs data/raw data/processed data/features data/predictions models
echo "✓ Directories created"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
read -p "Install dependencies in virtual environment? (y/n): " install_deps

if [ "$install_deps" = "y" ]; then
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Upgrade pip
    echo "Upgrading pip..."
    pip install --upgrade pip

    # Install dependencies
    echo "Installing dependencies (this may take a few minutes)..."
    pip install -e ".[dev]"

    echo "✓ Dependencies installed"

    # Install pre-commit hooks
    echo "Installing pre-commit hooks..."
    pre-commit install
    echo "✓ Pre-commit hooks installed"
fi

# Initialize DVC
echo ""
read -p "Initialize DVC? (y/n): " init_dvc
if [ "$init_dvc" = "y" ]; then
    bash scripts/setup_dvc.sh
fi

# Start Docker services
echo ""
read -p "Start Docker services now? (y/n): " start_docker

if [ "$start_docker" = "y" ]; then
    echo "Starting Docker services..."
    cd infrastructure
    docker-compose up -d
    cd ..

    echo ""
    echo "Waiting for services to be ready (30 seconds)..."
    sleep 30

    echo ""
    echo "========================================="
    echo "Services are starting!"
    echo "========================================="
    echo ""
    echo "Access your services at:"
    echo "  • Airflow UI:    http://localhost:8080 (admin/admin)"
    echo "  • MLflow UI:     http://localhost:5000"
    echo "  • FastAPI Docs:  http://localhost:8000/docs"
    echo "  • Streamlit:     http://localhost:8501"
    echo "  • Grafana:       http://localhost:3000 (admin/admin)"
    echo "  • Prometheus:    http://localhost:9090"
    echo ""
    echo "Check service status:"
    echo "  docker-compose -f infrastructure/docker-compose.yml ps"
    echo ""
    echo "View logs:"
    echo "  docker-compose -f infrastructure/docker-compose.yml logs -f"
    echo ""
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Ensure your OpenWeatherMap API key is set in .env"
echo "2. Start services: cd infrastructure && docker-compose up -d"
echo "3. Access Airflow UI at http://localhost:8080"
echo "4. Trigger data ingestion DAG"
echo "5. Explore the documentation in README.md"
echo ""
echo "For development:"
echo "  source .venv/bin/activate  # Activate virtual environment"
echo "  pytest                     # Run tests"
echo "  pre-commit run --all-files # Run code quality checks"
echo ""
