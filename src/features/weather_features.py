"""
Weather Feature Engineering
Generates weather-based features for bike demand forecasting
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger

from src.features.base_features import BaseFeatureGenerator


class WeatherFeatureGenerator(BaseFeatureGenerator):
    """Generator for weather-based features"""

    def __init__(self, feature_version: str = "v1.0"):
        """
        Initialize weather feature generator

        Args:
            feature_version: Version identifier
        """
        super().__init__(feature_version)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate weather features

        Args:
            df: Input DataFrame with weather columns

        Returns:
            DataFrame with weather features added
        """
        logger.info("Generating weather features")

        original_cols = len(df.columns)
        df = df.copy()

        # Temperature features (if available)
        if "temperature" in df.columns:
            # Normalized temperature (0-1 scale, assuming -20 to 40°C range)
            df["temperature_normalized"] = (df["temperature"] + 20) / 60
            df["temperature_normalized"] = df["temperature_normalized"].clip(0, 1)
            self.feature_names.append("temperature_normalized")

            # Temperature categories
            df["temp_category"] = pd.cut(
                df["temperature"],
                bins=[-np.inf, 0, 10, 20, 30, np.inf],
                labels=["freezing", "cold", "mild", "warm", "hot"]
            )
            self.feature_names.append("temp_category")

            # Is comfortable temperature (15-25°C)
            df["is_comfortable_temp"] = df["temperature"].between(15, 25).astype(int)
            self.feature_names.append("is_comfortable_temp")

        # Feels like temperature
        if "feels_like" in df.columns:
            df["feels_like_normalized"] = (df["feels_like"] + 20) / 60
            df["feels_like_normalized"] = df["feels_like_normalized"].clip(0, 1)
            self.feature_names.append("feels_like_normalized")

            # Temperature comfort difference
            if "temperature" in df.columns:
                df["temp_feels_diff"] = df["temperature"] - df["feels_like"]
                self.feature_names.append("temp_feels_diff")

        # Humidity features
        if "humidity" in df.columns:
            # Humidity normalized
            df["humidity_normalized"] = df["humidity"] / 100
            self.feature_names.append("humidity_normalized")

            # Humidity categories
            df["humidity_category"] = pd.cut(
                df["humidity"],
                bins=[0, 30, 60, 80, 100],
                labels=["low", "medium", "high", "very_high"]
            )
            self.feature_names.append("humidity_category")

        # Wind speed features
        if "wind_speed" in df.columns:
            # Wind categories (Beaufort scale simplified)
            df["wind_category"] = pd.cut(
                df["wind_speed"],
                bins=[0, 5, 10, 15, np.inf],
                labels=["calm", "breezy", "windy", "strong"]
            )
            self.feature_names.append("wind_category")

            # Is windy (> 10 m/s)
            df["is_windy"] = (df["wind_speed"] > 10).astype(int)
            self.feature_names.append("is_windy")

        # Precipitation features
        if "precipitation" in df.columns:
            # Is rainy
            df["is_rainy"] = (df["precipitation"] > 0).astype(int)
            self.feature_names.append("is_rainy")

            # Rain intensity categories
            df["rain_intensity"] = pd.cut(
                df["precipitation"],
                bins=[0, 0.1, 2.5, 10, np.inf],
                labels=["none", "light", "moderate", "heavy"]
            )
            self.feature_names.append("rain_intensity")

        # Weather condition features
        if "weather_condition" in df.columns:
            # Boolean flags for major weather conditions
            df["is_clear"] = (df["weather_condition"].str.lower() == "clear").astype(int)
            df["is_cloudy"] = (df["weather_condition"].str.lower().str.contains("cloud")).astype(int)
            df["is_rain"] = (df["weather_condition"].str.lower().str.contains("rain")).astype(int)
            df["is_snow"] = (df["weather_condition"].str.lower().str.contains("snow")).astype(int)
            df["is_storm"] = (df["weather_condition"].str.lower().str.contains("storm|thunder")).astype(int)

            self.feature_names.extend(["is_clear", "is_cloudy", "is_rain", "is_snow", "is_storm"])

            # Weather severity score (0-5)
            df["weather_severity"] = 0
            df.loc[df["is_clear"] == 1, "weather_severity"] = 1
            df.loc[df["is_cloudy"] == 1, "weather_severity"] = 2
            df.loc[df["is_rain"] == 1, "weather_severity"] = 3
            df.loc[df["is_snow"] == 1, "weather_severity"] = 4
            df.loc[df["is_storm"] == 1, "weather_severity"] = 5
            self.feature_names.append("weather_severity")

        # Visibility features
        if "visibility" in df.columns:
            # Normalized visibility (assuming max 10km)
            df["visibility_normalized"] = (df["visibility"] / 10000).clip(0, 1)
            self.feature_names.append("visibility_normalized")

            # Poor visibility
            df["is_poor_visibility"] = (df["visibility"] < 1000).astype(int)
            self.feature_names.append("is_poor_visibility")

        # Pressure features
        if "pressure" in df.columns:
            # Pressure normalized (assuming 980-1040 hPa range)
            df["pressure_normalized"] = (df["pressure"] - 980) / 60
            df["pressure_normalized"] = df["pressure_normalized"].clip(0, 1)
            self.feature_names.append("pressure_normalized")

        # Composite bad weather index
        bad_weather_score = 0
        if "is_rainy" in df.columns:
            bad_weather_score += df["is_rainy"] * 2
        if "is_windy" in df.columns:
            bad_weather_score += df["is_windy"]
        if "is_snow" in df.columns:
            bad_weather_score += df["is_snow"] * 3
        if "is_comfortable_temp" in df.columns:
            bad_weather_score += (1 - df["is_comfortable_temp"])

        if isinstance(bad_weather_score, pd.Series):
            df["bad_weather_index"] = bad_weather_score
            self.feature_names.append("bad_weather_index")

        self.log_generation_summary(df, original_cols)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of generated feature names"""
        return self.feature_names


# Convenience function
def generate_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate weather features from DataFrame

    Args:
        df: Input DataFrame with weather columns

    Returns:
        DataFrame with weather features
    """
    generator = WeatherFeatureGenerator()
    return generator.generate(df)
