"""
Prediction Router
API endpoints for bike demand predictions
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from loguru import logger

from src.serving.api.schemas.prediction_schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ForecastRequest,
    ForecastResponse,
    ErrorResponse
)
from src.serving.predictor import get_predictor

router = APIRouter(
    prefix="/predict",
    tags=["predictions"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        400: {"model": ErrorResponse, "description": "Bad request"},
    }
)


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict bike demand",
    description="Predict bike availability for a single station at a specific time"
)
async def predict_demand(request: PredictionRequest) -> PredictionResponse:
    """
    Predict bike demand for a single station

    - **station_id**: ID of the bike station
    - **timestamp**: Optional prediction timestamp (default: now + 1 hour)
    - **weather_data**: Optional weather conditions
    """
    try:
        logger.info(f"Received prediction request for station {request.station_id}")

        predictor = get_predictor()

        # Convert weather data to dict if provided
        weather_dict = None
        if request.weather_data:
            weather_dict = request.weather_data.model_dump(exclude_none=True)

        # Make prediction
        result = predictor.predict(
            station_id=request.station_id,
            timestamp=request.timestamp,
            weather_data=weather_dict
        )

        return PredictionResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch predict bike demand",
    description="Predict bike availability for multiple stations/times (max 100)"
)
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """
    Make batch predictions for multiple stations/times

    - **predictions**: List of prediction requests (max 100)

    Returns predictions and success/failure counts
    """
    try:
        logger.info(f"Received batch prediction request with {len(request.predictions)} items")

        predictor = get_predictor()

        # Convert requests to list of dicts
        predictions_list = []
        for pred_req in request.predictions:
            pred_dict = {
                "station_id": pred_req.station_id,
                "timestamp": pred_req.timestamp,
                "weather_data": pred_req.weather_data.model_dump(exclude_none=True) if pred_req.weather_data else None
            }
            predictions_list.append(pred_dict)

        # Make batch predictions
        results = predictor.predict_batch(predictions_list)

        # Count successes and failures
        successful = sum(1 for r in results if "error" not in r)
        failed = len(results) - successful

        # Convert successful results to response models
        prediction_responses = []
        for result in results:
            if "error" not in result:
                prediction_responses.append(PredictionResponse(**result))

        return BatchPredictionResponse(
            predictions=prediction_responses,
            total_predictions=len(results),
            successful=successful,
            failed=failed
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@router.post(
    "/station/{station_id}/forecast",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-hour forecast",
    description="Generate multi-hour demand forecast for a station (max 168 hours)"
)
async def forecast_demand(
    station_id: str,
    hours_ahead: int = 24,
    start_time: datetime = None
) -> ForecastResponse:
    """
    Generate multi-hour forecast for a station

    - **station_id**: ID of the bike station
    - **hours_ahead**: Number of hours to forecast (1-168, default 24)
    - **start_time**: Optional forecast start time (default: now)
    """
    try:
        logger.info(f"Received forecast request for station {station_id}, {hours_ahead} hours")

        # Validate hours_ahead
        if hours_ahead < 1 or hours_ahead > 168:
            raise ValueError("hours_ahead must be between 1 and 168")

        predictor = get_predictor()

        # Make forecast
        result = predictor.forecast(
            station_id=station_id,
            hours_ahead=hours_ahead,
            start_time=start_time
        )

        return ForecastResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Forecast failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {str(e)}"
        )


@router.get(
    "/station/{station_id}/forecast",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-hour forecast (GET)",
    description="Generate multi-hour demand forecast for a station via GET request"
)
async def forecast_demand_get(
    station_id: str,
    hours_ahead: int = 24
) -> ForecastResponse:
    """
    Generate multi-hour forecast for a station (GET method)

    - **station_id**: ID of the bike station
    - **hours_ahead**: Number of hours to forecast (1-168, default 24)
    """
    return await forecast_demand(station_id, hours_ahead, None)
