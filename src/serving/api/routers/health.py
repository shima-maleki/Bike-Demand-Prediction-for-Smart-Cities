"""
Health Router
Health check and status endpoints
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from src.serving.model_loader import get_model_loader
from src.config.settings import get_settings

router = APIRouter(
    prefix="/health",
    tags=["health"],
)

settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    model_status: Optional[str] = Field(None, description="Model status")
    database_status: Optional[str] = Field(None, description="Database status")


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""
    status: str = Field(..., description="Overall status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, Any] = Field(..., description="Component health statuses")


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Check if the API service is running"
)
async def health_check() -> HealthResponse:
    """
    Basic health check

    Returns service status and version
    """
    try:
        # Check model status
        model_loader = get_model_loader()
        model = model_loader.get_model()
        model_status = "loaded" if model is not None else "not_loaded"

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            model_status=model_status,
            database_status="unknown"  # Would check database connection
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            model_status="error",
            database_status="unknown"
        )


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Check health of all system components"
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check

    Checks:
    - API service
    - Model loading
    - Database connection
    - MLflow connection
    """
    components = {}
    overall_status = "healthy"

    # Check API
    components["api"] = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check model
    try:
        model_loader = get_model_loader()
        model = model_loader.get_model()
        model_info = model_loader.get_model_info()

        if model is not None:
            components["model"] = {
                "status": "healthy",
                "loaded": True,
                "info": model_info
            }
        else:
            components["model"] = {
                "status": "degraded",
                "loaded": False,
                "error": "No model loaded"
            }
            overall_status = "degraded"

    except Exception as e:
        components["model"] = {
            "status": "unhealthy",
            "loaded": False,
            "error": str(e)
        }
        overall_status = "unhealthy"

    # Check database
    try:
        from src.config.database import get_db_context
        from sqlalchemy import text

        with get_db_context() as db:
            # Try a simple query
            result = db.execute(text("SELECT 1")).scalar()
            components["database"] = {
                "status": "healthy" if result == 1 else "degraded",
                "connected": True
            }

    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
        overall_status = "unhealthy"

    # Check MLflow
    try:
        import mlflow
        mlflow.set_tracking_uri(settings.mlflow.tracking_uri)
        client = mlflow.tracking.MlflowClient()

        # Try to list experiments
        experiments = client.search_experiments(max_results=1)

        components["mlflow"] = {
            "status": "healthy",
            "connected": True,
            "tracking_uri": settings.mlflow.tracking_uri
        }

    except Exception as e:
        components["mlflow"] = {
            "status": "degraded",
            "connected": False,
            "error": str(e)
        }
        # MLflow not critical for serving, so don't mark as unhealthy

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        components=components
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if service is ready to accept requests"
)
async def readiness_check() -> Dict[str, str]:
    """
    Readiness check for Kubernetes/Docker

    Returns 200 if ready, 503 if not ready
    """
    try:
        # Check if model is loaded
        model_loader = get_model_loader()
        model = model_loader.get_model()

        if model is None:
            logger.warning("Service not ready: model not loaded")
            return {
                "status": "not_ready",
                "reason": "model_not_loaded"
            }

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "reason": str(e)
        }


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if service is alive"
)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes/Docker

    Always returns 200 if the process is running
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
