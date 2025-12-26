"""
Monitoring Router
Prometheus metrics and monitoring endpoints
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from src.serving.model_loader import get_model_loader

router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
)


class ModelMetrics(BaseModel):
    """Model performance metrics"""
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")
    test_rmse: Optional[float] = Field(None, description="Test RMSE")
    test_mae: Optional[float] = Field(None, description="Test MAE")
    test_mape: Optional[float] = Field(None, description="Test MAPE")
    test_r2: Optional[float] = Field(None, description="Test R²")
    val_rmse: Optional[float] = Field(None, description="Validation RMSE")
    val_mae: Optional[float] = Field(None, description="Validation MAE")
    val_mape: Optional[float] = Field(None, description="Validation MAPE")
    val_r2: Optional[float] = Field(None, description="Validation R²")


class CurrentModelResponse(BaseModel):
    """Current model information"""
    model_info: Dict[str, Any] = Field(..., description="Model metadata")
    metrics: Optional[ModelMetrics] = Field(None, description="Model performance metrics")
    timestamp: str = Field(..., description="Response timestamp")


@router.get(
    "/models/current",
    response_model=CurrentModelResponse,
    summary="Get current model info",
    description="Get information about the currently loaded model"
)
async def get_current_model() -> CurrentModelResponse:
    """
    Get current model information and metrics

    Returns model metadata and performance metrics from MLflow
    """
    try:
        model_loader = get_model_loader()
        model_info = model_loader.get_model_info()
        model_metrics = model_loader.get_model_metrics()

        # Convert metrics dict to ModelMetrics if available
        metrics_obj = None
        if model_metrics:
            model_version = model_info.get("version") if model_info else None
            # Convert version to string if it's an integer
            if model_version is not None and not isinstance(model_version, str):
                model_version = str(model_version)

            metrics_obj = ModelMetrics(
                model_name=model_info.get("name") if model_info else None,
                model_version=model_version,
                **model_metrics
            )

        return CurrentModelResponse(
            model_info=model_info or {},
            metrics=metrics_obj,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to get current model: {e}")
        return CurrentModelResponse(
            model_info={},
            metrics=None,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Prometheus-compatible metrics endpoint",
    response_class=Response
)
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format:
    - Model status
    - API request counts
    - Prediction latency
    - Model performance metrics
    """
    try:
        metrics_lines = []

        # Model status metrics
        model_loader = get_model_loader()
        model = model_loader.get_model()
        model_info = model_loader.get_model_info()

        model_loaded = 1 if model is not None else 0
        metrics_lines.append(f"# HELP bike_demand_model_loaded Model loaded status")
        metrics_lines.append(f"# TYPE bike_demand_model_loaded gauge")
        metrics_lines.append(f'bike_demand_model_loaded{{model_name="{model_info.get("name", "unknown") if model_info else "unknown"}"}} {model_loaded}')

        # Model version
        if model_info and "version" in model_info:
            metrics_lines.append(f"# HELP bike_demand_model_version Current model version")
            metrics_lines.append(f"# TYPE bike_demand_model_version gauge")
            metrics_lines.append(f'bike_demand_model_version{{model_name="{model_info.get("name", "unknown")}"}} {model_info.get("version", 0)}')

        # Model performance metrics
        model_metrics = model_loader.get_model_metrics()
        if model_metrics:
            # Test RMSE
            if "test_rmse" in model_metrics:
                metrics_lines.append(f"# HELP bike_demand_model_test_rmse Model test RMSE")
                metrics_lines.append(f"# TYPE bike_demand_model_test_rmse gauge")
                metrics_lines.append(f'bike_demand_model_test_rmse{{model_name="{model_info.get("name", "unknown")}"}} {model_metrics["test_rmse"]}')

            # Test MAE
            if "test_mae" in model_metrics:
                metrics_lines.append(f"# HELP bike_demand_model_test_mae Model test MAE")
                metrics_lines.append(f"# TYPE bike_demand_model_test_mae gauge")
                metrics_lines.append(f'bike_demand_model_test_mae{{model_name="{model_info.get("name", "unknown")}"}} {model_metrics["test_mae"]}')

            # Test MAPE
            if "test_mape" in model_metrics:
                metrics_lines.append(f"# HELP bike_demand_model_test_mape Model test MAPE")
                metrics_lines.append(f"# TYPE bike_demand_model_test_mape gauge")
                metrics_lines.append(f'bike_demand_model_test_mape{{model_name="{model_info.get("name", "unknown")}"}} {model_metrics["test_mape"]}')

            # Test R²
            if "test_r2" in model_metrics:
                metrics_lines.append(f"# HELP bike_demand_model_test_r2 Model test R²")
                metrics_lines.append(f"# TYPE bike_demand_model_test_r2 gauge")
                metrics_lines.append(f'bike_demand_model_test_r2{{model_name="{model_info.get("name", "unknown")}"}} {model_metrics["test_r2"]}')

        # Database connection status
        try:
            from src.config.database import get_db_context

            with get_db_context() as db:
                result = db.execute(text("SELECT 1")).scalar()
                db_connected = 1 if result == 1 else 0

        except Exception:
            db_connected = 0

        metrics_lines.append(f"# HELP bike_demand_database_connected Database connection status")
        metrics_lines.append(f"# TYPE bike_demand_database_connected gauge")
        metrics_lines.append(f"bike_demand_database_connected {db_connected}")

        # System uptime (placeholder - would track actual uptime)
        metrics_lines.append(f"# HELP bike_demand_uptime_seconds Service uptime in seconds")
        metrics_lines.append(f"# TYPE bike_demand_uptime_seconds counter")
        metrics_lines.append(f"bike_demand_uptime_seconds 0")

        # Join all metrics with newlines
        metrics_text = "\n".join(metrics_lines) + "\n"

        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain"
        )


@router.post(
    "/models/reload",
    summary="Reload model",
    description="Reload the production model from MLflow"
)
async def reload_model() -> Dict[str, Any]:
    """
    Reload the production model

    Useful for deploying new model versions without restarting the service
    """
    try:
        logger.info("Manual model reload requested")

        model_loader = get_model_loader()
        old_info = model_loader.get_model_info()

        # Reload production model
        model_loader.load_production_model()
        new_info = model_loader.get_model_info()

        return {
            "status": "success",
            "message": "Model reloaded successfully",
            "old_model": old_info,
            "new_model": new_info,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Model reload failed: {e}")
        return {
            "status": "error",
            "message": f"Model reload failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get(
    "/stats",
    summary="API statistics",
    description="Get API usage statistics"
)
async def get_stats() -> Dict[str, Any]:
    """
    Get API usage statistics

    In production, this would track:
    - Total predictions made
    - Average response time
    - Error rate
    - Predictions by station
    """
    # Placeholder - would track real stats in production
    return {
        "total_predictions": 0,
        "total_forecasts": 0,
        "average_response_time_ms": 0.0,
        "error_rate": 0.0,
        "uptime_seconds": 0,
        "timestamp": datetime.utcnow().isoformat()
    }
