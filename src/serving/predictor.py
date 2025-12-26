"""
Predictor
Handles prediction logic for bike demand forecasting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.serving.model_loader import get_model_loader
from src.features.temporal_features import TemporalFeatureGenerator
from src.features.weather_features import WeatherFeatureGenerator
from src.features.lag_features import LagFeatureGenerator
from src.features.rolling_features import RollingFeatureGenerator
from src.features.holiday_features import HolidayFeatureGenerator
from src.data.storage.postgres_handler import PostgreSQLHandler


class BikeDedemandPredictor:
    """Predicts bike demand for stations"""

    def __init__(self):
        """Initialize predictor"""
        self.model_loader = get_model_loader()
        self.postgres = PostgreSQLHandler()

        # Initialize feature generators
        self.temporal_gen = TemporalFeatureGenerator()
        self.weather_gen = WeatherFeatureGenerator()
        self.lag_gen = LagFeatureGenerator(
            lag_hours=[1, 3, 6, 12, 24, 48, 168],
            target_column="bikes_available"
        )
        self.rolling_gen = RollingFeatureGenerator(
            windows=[3, 6, 12, 24],
            statistics=["mean", "std", "min", "max"],
            target_column="bikes_available"
        )
        self.holiday_gen = HolidayFeatureGenerator()

    def predict(
        self,
        station_id: str,
        timestamp: Optional[datetime] = None,
        weather_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict bike demand for a single station at a specific time

        Args:
            station_id: Station ID
            timestamp: Prediction timestamp (default: now + 1 hour)
            weather_data: Optional weather data dict

        Returns:
            Dictionary with prediction and metadata
        """
        if timestamp is None:
            timestamp = datetime.utcnow() + timedelta(hours=1)

        logger.info(f"Predicting demand for station {station_id} at {timestamp}")

        try:
            # Get model
            model = self.model_loader.get_model()
            if model is None:
                raise ValueError("No model loaded")

            # Prepare features
            features = self._prepare_features(station_id, timestamp, weather_data)

            # Make prediction
            prediction = model.predict(features)[0]

            # Get confidence interval (simple std-based estimate)
            # In production, use proper prediction intervals
            std_error = prediction * 0.15  # Assume 15% error
            confidence_lower = max(0, prediction - 1.96 * std_error)
            confidence_upper = prediction + 1.96 * std_error

            # Get model info and ensure version is a string
            model_info = self.model_loader.get_model_info()
            if model_info and "version" in model_info:
                model_info["version"] = str(model_info["version"])

            result = {
                "station_id": station_id,
                "timestamp": timestamp.isoformat(),
                "predicted_demand": float(prediction),
                "confidence_interval": {
                    "lower": float(confidence_lower),
                    "upper": float(confidence_upper),
                    "confidence_level": 0.95
                },
                "model_info": model_info,
                "prediction_made_at": datetime.utcnow().isoformat()
            }

            logger.info(f"✓ Predicted demand: {prediction:.2f} bikes")

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise

    def predict_batch(
        self,
        predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Predict bike demand for multiple station/time combinations

        Args:
            predictions: List of dicts with station_id, timestamp, weather_data

        Returns:
            List of prediction results
        """
        logger.info(f"Making batch predictions for {len(predictions)} requests")

        results = []

        for pred_request in predictions:
            try:
                result = self.predict(
                    station_id=pred_request["station_id"],
                    timestamp=pred_request.get("timestamp"),
                    weather_data=pred_request.get("weather_data")
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Batch prediction failed for {pred_request.get('station_id')}: {e}")
                results.append({
                    "station_id": pred_request.get("station_id"),
                    "error": str(e),
                    "prediction_made_at": datetime.utcnow().isoformat()
                })

        logger.info(f"✓ Completed {len(results)} batch predictions")

        return results

    def forecast(
        self,
        station_id: str,
        hours_ahead: int = 24,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate multi-hour forecast for a station

        Args:
            station_id: Station ID
            hours_ahead: Number of hours to forecast
            start_time: Start time (default: now)

        Returns:
            Dictionary with forecast array and metadata
        """
        if start_time is None:
            start_time = datetime.utcnow()

        logger.info(f"Generating {hours_ahead}h forecast for station {station_id}")

        try:
            forecasts = []

            for hour in range(1, hours_ahead + 1):
                forecast_time = start_time + timedelta(hours=hour)

                # Make prediction
                result = self.predict(
                    station_id=station_id,
                    timestamp=forecast_time,
                    weather_data=None  # Would fetch forecast weather in production
                )

                forecasts.append({
                    "timestamp": forecast_time.isoformat(),
                    "hour_ahead": hour,
                    "predicted_demand": result["predicted_demand"],
                    "confidence_interval": result["confidence_interval"]
                })

            return {
                "station_id": station_id,
                "forecast_start": start_time.isoformat(),
                "forecast_hours": hours_ahead,
                "forecasts": forecasts,
                "model_info": self.model_loader.get_model_info(),
                "forecast_made_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            raise

    def _prepare_features(
        self,
        station_id: str,
        timestamp: datetime,
        weather_data: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Prepare features for prediction

        NOTE: This is a simplified version for the demo model.
        For production, use the full feature engineering pipeline.

        Args:
            station_id: Station ID
            timestamp: Prediction timestamp
            weather_data: Optional weather data

        Returns:
            DataFrame with features matching the model's training features
        """
        # Check what features the model expects
        model = self.model_loader.get_model()
        if model is None:
            raise ValueError("No model loaded")

        # Try to get feature names from the model
        try:
            model_features = model.feature_names_in_
            logger.info(f"Model expects features: {list(model_features)}")
            use_simple_features = len(model_features) < 10
        except AttributeError:
            # Model doesn't have feature_names_in_, assume simple features
            use_simple_features = True
            logger.warning("Model doesn't expose feature names, using simple features")

        if use_simple_features:
            # Simple features for demo model (hour, day_of_week, temperature, humidity)
            df = pd.DataFrame({
                "hour": [timestamp.hour],
                "day_of_week": [timestamp.weekday()],
                "temperature": [weather_data.get("temperature", 20.0) if weather_data else 20.0],
                "humidity": [weather_data.get("humidity", 60.0) if weather_data else 60.0]
            })
            logger.info("Using simple feature set for demo model")
            return df

        # Full feature engineering for production model
        # Create base dataframe
        df = pd.DataFrame({
            "station_id": [station_id],
            "timestamp": [timestamp],
            "bikes_available": [0]  # Placeholder for target
        })

        # Generate temporal features
        df = self.temporal_gen.generate(df)

        # Add weather features if provided
        if weather_data:
            for key, value in weather_data.items():
                df[key] = value
            df = self.weather_gen.generate(df)
        else:
            # Try to get latest weather from database
            try:
                latest_weather = self._get_latest_weather()
                if latest_weather:
                    for key, value in latest_weather.items():
                        if key != "timestamp":
                            df[key] = value
                    df = self.weather_gen.generate(df)
            except Exception as e:
                logger.warning(f"Could not fetch weather data: {e}")

        # Add holiday features
        df = self.holiday_gen.generate(df)

        # Get historical data for lag and rolling features
        try:
            historical_data = self._get_historical_data(station_id, timestamp)

            if historical_data is not None and len(historical_data) > 0:
                # Combine historical with current
                combined = pd.concat([historical_data, df], ignore_index=True)

                # Generate lag features
                combined = self.lag_gen.generate(combined)

                # Generate rolling features
                combined = self.rolling_gen.generate(combined)

                # Get only the last row (our prediction point)
                df = combined.tail(1).copy()
            else:
                logger.warning("No historical data available for lag/rolling features")

        except Exception as e:
            logger.warning(f"Could not generate lag/rolling features: {e}")

        # Remove target column
        if "bikes_available" in df.columns:
            df = df.drop(columns=["bikes_available"])

        # Remove non-feature columns
        non_feature_cols = ["station_id", "timestamp", "date", "holiday_name"]
        df = df.drop(columns=[c for c in non_feature_cols if c in df.columns])

        # Ensure feature order matches model
        try:
            df = df[model_features]
        except KeyError as e:
            logger.error(f"Missing features: {e}")
            raise ValueError(f"Required features not available: {e}")

        return df

    def _get_historical_data(
        self,
        station_id: str,
        timestamp: datetime,
        lookback_hours: int = 168
    ) -> Optional[pd.DataFrame]:
        """
        Get historical data for lag/rolling features

        Args:
            station_id: Station ID
            timestamp: Current timestamp
            lookback_hours: Hours to look back

        Returns:
            DataFrame with historical data or None
        """
        try:
            from src.config.database import get_db_context
            from sqlalchemy import select, and_
            from src.data.models import BikeStationStatus

            start_time = timestamp - timedelta(hours=lookback_hours)

            with get_db_context() as db:
                query = select(BikeStationStatus).where(
                    and_(
                        BikeStationStatus.station_id == station_id,
                        BikeStationStatus.timestamp >= start_time,
                        BikeStationStatus.timestamp < timestamp
                    )
                ).order_by(BikeStationStatus.timestamp)

                df = pd.read_sql(query, db.connection())

                if len(df) > 0:
                    return df
                else:
                    logger.warning(f"No historical data found for station {station_id}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return None

    def _get_latest_weather(self) -> Optional[Dict[str, Any]]:
        """
        Get latest weather data from database

        Returns:
            Dictionary with weather data or None
        """
        try:
            from src.config.database import get_db_context
            from sqlalchemy import select
            from src.data.models import WeatherData

            with get_db_context() as db:
                query = select(WeatherData).order_by(
                    WeatherData.timestamp.desc()
                ).limit(1)

                result = db.execute(query).first()

                if result:
                    weather = result[0]
                    return {
                        "temperature": weather.temperature,
                        "feels_like": weather.feels_like,
                        "humidity": weather.humidity,
                        "wind_speed": weather.wind_speed,
                        "precipitation": weather.precipitation or 0,
                        "weather_condition": weather.weather_condition,
                        "visibility": weather.visibility,
                        "pressure": weather.pressure
                    }
                else:
                    return None

        except Exception as e:
            logger.error(f"Failed to get latest weather: {e}")
            return None


# Global predictor instance
_predictor = None


def get_predictor() -> BikeDedemandPredictor:
    """
    Get or create global predictor instance

    Returns:
        BikeDedemandPredictor instance
    """
    global _predictor

    if _predictor is None:
        _predictor = BikeDedemandPredictor()

    return _predictor
