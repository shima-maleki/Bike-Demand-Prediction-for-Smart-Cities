"""
FastAPI Application
Main API application for bike demand prediction serving
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime
from loguru import logger
import time

from src.serving.api.routers import predictions, health, monitoring
from src.config.settings import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Bike Demand Prediction API",
    description="""
    🚴 **Bike Demand Forecasting API**

    Production-grade ML serving API for predicting bike station demand in smart cities.

    ## Features

    * **Single Predictions**: Predict demand for a specific station and time
    * **Batch Predictions**: Predict demand for multiple stations efficiently
    * **Multi-hour Forecasts**: Generate forecasts up to 7 days ahead
    * **Health Checks**: Kubernetes-compatible readiness and liveness probes
    * **Monitoring**: Prometheus metrics for observability

    ## Model

    Uses gradient boosting models (XGBoost/LightGBM/CatBoost) trained on:
    - 100+ engineered features (temporal, lag, rolling, weather, holiday)
    - Historical bike station data
    - Weather enrichment
    - Holiday detection

    ## MLOps

    - Models managed via MLflow Model Registry
    - Automated training pipeline with Airflow
    - Data versioning with DVC
    - CI/CD with GitHub Actions
    """,
    version="1.0.0",
    contact={
        "name": "Bike Demand Prediction Team",
        "url": "https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities",
    },
    license_info={
        "name": "MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests with timing"""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"

    # Log request
    logger.info(
        f"Request {request_id}: {request.method} {request.url.path}"
    )

    # Process request
    try:
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Response {request_id}: {response.status_code} ({duration_ms:.2f}ms)"
        )

        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error {request_id}: {str(e)} ({duration_ms:.2f}ms)"
        )
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


# Include routers
app.include_router(predictions.router)
app.include_router(health.router)
app.include_router(monitoring.router)


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="API root",
    description="API information and links"
)
async def root():
    """
    API root endpoint

    Returns API information and links to documentation
    """
    return {
        "name": "Bike Demand Prediction API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "health_check": "/health",
        "metrics": "/monitoring/metrics",
        "github": "https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup

    - Log startup information
    - Initialize model loader
    - Check database connection
    """
    logger.info("=" * 70)
    logger.info("STARTING BIKE DEMAND PREDICTION API")
    logger.info("=" * 70)
    logger.info(f"Version: 1.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"MLflow Tracking URI: {settings.mlflow.tracking_uri}")
    logger.info("=" * 70)

    try:
        # Initialize model loader (loads production model)
        from src.serving.model_loader import get_model_loader

        model_loader = get_model_loader()
        model_info = model_loader.get_model_info()

        if model_info:
            logger.info("✓ Model loaded successfully")
            logger.info(f"  Model: {model_info.get('name')}")
            logger.info(f"  Version: {model_info.get('version')}")
            logger.info(f"  Stage: {model_info.get('stage')}")
        else:
            logger.warning("⚠ No production model found")

    except Exception as e:
        logger.error(f"Failed to load model on startup: {e}")
        logger.warning("API will start but predictions may fail")

    # Check database
    try:
        from src.config.database import get_db_context

        with get_db_context() as db:
            result = db.execute("SELECT 1").scalar()
            if result == 1:
                logger.info("✓ Database connection successful")
            else:
                logger.warning("⚠ Database connection issue")

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.warning("API will start but database-dependent features may fail")

    logger.info("=" * 70)
    logger.info("API READY TO ACCEPT REQUESTS")
    logger.info("=" * 70)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("=" * 70)
    logger.info("SHUTTING DOWN BIKE DEMAND PREDICTION API")
    logger.info("=" * 70)
    logger.info("✓ Shutdown complete")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")

    uvicorn.run(
        "src.serving.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
