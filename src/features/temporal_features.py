"""
Temporal Feature Engineering
Generates time-based features from timestamp
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger

from src.features.base_features import BaseFeatureGenerator


class TemporalFeatureGenerator(BaseFeatureGenerator):
    """Generator for temporal/time-based features"""

    def __init__(self, timestamp_column: str = "timestamp", feature_version: str = "v1.0"):
        """
        Initialize temporal feature generator

        Args:
            timestamp_column: Name of timestamp column
            feature_version: Version identifier
        """
        super().__init__(feature_version)
        self.timestamp_column = timestamp_column

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate temporal features

        Args:
            df: Input DataFrame with timestamp column

        Returns:
            DataFrame with temporal features added
        """
        logger.info("Generating temporal features")

        # Validate input
        if not self.validate_input(df, [self.timestamp_column]):
            raise ValueError(f"Missing required column: {self.timestamp_column}")

        original_cols = len(df.columns)
        df = df.copy()

        # Ensure timestamp is datetime
        df[self.timestamp_column] = pd.to_datetime(df[self.timestamp_column])
        dt = df[self.timestamp_column]

        # Basic temporal features
        df["hour_of_day"] = dt.dt.hour
        df["day_of_week"] = dt.dt.dayofweek  # Monday=0, Sunday=6
        df["day_of_month"] = dt.dt.day
        df["month"] = dt.dt.month
        df["quarter"] = dt.dt.quarter
        df["year"] = dt.dt.year
        df["week_of_year"] = dt.dt.isocalendar().week

        # Boolean features
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)  # Saturday=5, Sunday=6
        df["is_weekday"] = (~df["is_weekend"].astype(bool)).astype(int)

        # Season (for northern hemisphere)
        df["season"] = df["month"].apply(self._get_season)

        # Part of day
        df["part_of_day"] = df["hour_of_day"].apply(self._get_part_of_day)

        # Rush hour (7-9 AM, 5-8 PM on weekdays)
        df["is_rush_hour"] = (
            ((df["hour_of_day"].between(7, 9) | df["hour_of_day"].between(17, 20)) &
             (df["is_weekday"] == 1))
        ).astype(int)

        # Morning/afternoon/evening/night
        df["is_morning"] = df["hour_of_day"].between(6, 12).astype(int)
        df["is_afternoon"] = df["hour_of_day"].between(12, 18).astype(int)
        df["is_evening"] = df["hour_of_day"].between(18, 22).astype(int)
        df["is_night"] = (~(df["is_morning"] | df["is_afternoon"] | df["is_evening"]).astype(bool)).astype(int)

        # Cyclic encoding for periodic features
        df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        # Update feature names
        self.feature_names = [col for col in df.columns if col not in [self.timestamp_column] and col not in df.columns[:original_cols]]

        self.log_generation_summary(df, original_cols)

        return df

    def _get_season(self, month: int) -> str:
        """
        Get season from month (Northern hemisphere)

        Args:
            month: Month (1-12)

        Returns:
            Season name
        """
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:  # 9, 10, 11
            return "fall"

    def _get_part_of_day(self, hour: int) -> str:
        """
        Get part of day from hour

        Args:
            hour: Hour (0-23)

        Returns:
            Part of day
        """
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:  # 22-23
            return "night"

    def get_feature_names(self) -> List[str]:
        """Get list of generated feature names"""
        return self.feature_names


# Convenience function
def generate_temporal_features(df: pd.DataFrame, timestamp_column: str = "timestamp") -> pd.DataFrame:
    """
    Generate temporal features from DataFrame

    Args:
        df: Input DataFrame
        timestamp_column: Name of timestamp column

    Returns:
        DataFrame with temporal features
    """
    generator = TemporalFeatureGenerator(timestamp_column=timestamp_column)
    return generator.generate(df)
