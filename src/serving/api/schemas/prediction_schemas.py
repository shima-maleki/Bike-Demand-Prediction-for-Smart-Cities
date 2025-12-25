"""
Pydantic Schemas for Prediction API
Request and response models for all prediction endpoints
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Schemas

class WeatherData(BaseModel):
    """Weather data for predictions"""
    temperature: Optional[float] = Field(None, description="Temperature in Celsius", ge=-50, le=60)
    feels_like: Optional[float] = Field(None, description="Feels like temperature in Celsius")
    humidity: Optional[int] = Field(None, description="Humidity percentage", ge=0, le=100)
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s", ge=0)
    precipitation: Optional[float] = Field(None, description="Precipitation in mm", ge=0)
    weather_condition: Optional[str] = Field(None, description="Weather condition (e.g., Clear, Rain)")
    visibility: Optional[int] = Field(None, description="Visibility in meters", ge=0)
    pressure: Optional[int] = Field(None, description="Atmospheric pressure in hPa", ge=800, le=1100)


class PredictionRequest(BaseModel):
    """Single prediction request"""
    station_id: str = Field(..., description="Bike station ID", min_length=1)
    timestamp: Optional[datetime] = Field(None, description="Prediction timestamp (default: now + 1h)")
    weather_data: Optional[WeatherData] = Field(None, description="Optional weather data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "station_id": "station_1",
                "timestamp": "2025-01-15T14:00:00",
                "weather_data": {
                    "temperature": 18.5,
                    "humidity": 65,
                    "wind_speed": 4.2,
                    "weather_condition": "Clear"
                }
            }
        }
    )


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""
    predictions: List[PredictionRequest] = Field(..., description="List of prediction requests", min_length=1, max_length=100)

    @field_validator('predictions')
    @classmethod
    def validate_batch_size(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 predictions per batch")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "predictions": [
                    {
                        "station_id": "station_1",
                        "timestamp": "2025-01-15T14:00:00"
                    },
                    {
                        "station_id": "station_2",
                        "timestamp": "2025-01-15T14:00:00"
                    }
                ]
            }
        }
    )


class ForecastRequest(BaseModel):
    """Multi-hour forecast request"""
    station_id: str = Field(..., description="Bike station ID", min_length=1)
    hours_ahead: int = Field(24, description="Number of hours to forecast", ge=1, le=168)
    start_time: Optional[datetime] = Field(None, description="Forecast start time (default: now)")

    @field_validator('hours_ahead')
    @classmethod
    def validate_hours(cls, v):
        if v > 168:
            raise ValueError("Maximum forecast horizon is 168 hours (7 days)")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "station_id": "station_1",
                "hours_ahead": 24,
                "start_time": "2025-01-15T12:00:00"
            }
        }
    )


# Response Schemas

class ConfidenceInterval(BaseModel):
    """Prediction confidence interval"""
    lower: float = Field(..., description="Lower bound of confidence interval")
    upper: float = Field(..., description="Upper bound of confidence interval")
    confidence_level: float = Field(..., description="Confidence level (e.g., 0.95 for 95%)")


class ModelInfo(BaseModel):
    """Information about the model used"""
    name: Optional[str] = Field(None, description="Model name")
    version: Optional[str] = Field(None, description="Model version")
    stage: Optional[str] = Field(None, description="Model stage (Production, Staging)")
    run_id: Optional[str] = Field(None, description="MLflow run ID")
    loaded_at: Optional[str] = Field(None, description="When model was loaded")


class PredictionResponse(BaseModel):
    """Single prediction response"""
    station_id: str = Field(..., description="Bike station ID")
    timestamp: str = Field(..., description="Prediction timestamp")
    predicted_demand: float = Field(..., description="Predicted number of bikes available")
    confidence_interval: ConfidenceInterval = Field(..., description="95% confidence interval")
    model_info: Optional[ModelInfo] = Field(None, description="Model metadata")
    prediction_made_at: str = Field(..., description="When prediction was made")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "station_id": "station_1",
                "timestamp": "2025-01-15T14:00:00",
                "predicted_demand": 12.5,
                "confidence_interval": {
                    "lower": 9.8,
                    "upper": 15.2,
                    "confidence_level": 0.95
                },
                "model_info": {
                    "name": "bike-demand-forecasting",
                    "version": "3",
                    "stage": "Production"
                },
                "prediction_made_at": "2025-01-15T13:00:00"
            }
        }
    )


class BatchPredictionResponse(BaseModel):
    """Batch prediction response"""
    predictions: List[PredictionResponse] = Field(..., description="List of predictions")
    total_predictions: int = Field(..., description="Total number of predictions")
    successful: int = Field(..., description="Number of successful predictions")
    failed: int = Field(..., description="Number of failed predictions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "predictions": [
                    {
                        "station_id": "station_1",
                        "timestamp": "2025-01-15T14:00:00",
                        "predicted_demand": 12.5,
                        "confidence_interval": {
                            "lower": 9.8,
                            "upper": 15.2,
                            "confidence_level": 0.95
                        }
                    }
                ],
                "total_predictions": 2,
                "successful": 2,
                "failed": 0
            }
        }
    )


class HourlyForecast(BaseModel):
    """Single hour forecast"""
    timestamp: str = Field(..., description="Forecast timestamp")
    hour_ahead: int = Field(..., description="Hours ahead from start")
    predicted_demand: float = Field(..., description="Predicted bikes available")
    confidence_interval: ConfidenceInterval = Field(..., description="95% confidence interval")


class ForecastResponse(BaseModel):
    """Multi-hour forecast response"""
    station_id: str = Field(..., description="Bike station ID")
    forecast_start: str = Field(..., description="Forecast start time")
    forecast_hours: int = Field(..., description="Number of hours forecasted")
    forecasts: List[HourlyForecast] = Field(..., description="Hourly forecasts")
    model_info: Optional[ModelInfo] = Field(None, description="Model metadata")
    forecast_made_at: str = Field(..., description="When forecast was made")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "station_id": "station_1",
                "forecast_start": "2025-01-15T12:00:00",
                "forecast_hours": 24,
                "forecasts": [
                    {
                        "timestamp": "2025-01-15T13:00:00",
                        "hour_ahead": 1,
                        "predicted_demand": 12.5,
                        "confidence_interval": {
                            "lower": 9.8,
                            "upper": 15.2,
                            "confidence_level": 0.95
                        }
                    }
                ],
                "model_info": {
                    "name": "bike-demand-forecasting",
                    "version": "3"
                },
                "forecast_made_at": "2025-01-15T12:00:00"
            }
        }
    )


# Error Response

class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Prediction failed",
                "detail": "Station not found",
                "timestamp": "2025-01-15T12:00:00"
            }
        }
    )
