"""
Lag Feature Engineering
Generates lag features for time-series forecasting
"""

import pandas as pd
from typing import List
from loguru import logger

from src.features.base_features import BaseFeatureGenerator


class LagFeatureGenerator(BaseFeatureGenerator):
    """Generator for lag features"""

    def __init__(
        self,
        lag_hours: List[int] = [1, 3, 6, 12, 24, 48, 168],
        target_column: str = "bikes_available",
        station_id_column: str = "station_id",
        timestamp_column: str = "timestamp",
        feature_version: str = "v1.0"
    ):
        """
        Initialize lag feature generator

        Args:
            lag_hours: List of lag periods in hours
            target_column: Column to create lags for
            station_id_column: Station identifier column
            timestamp_column: Timestamp column
            feature_version: Version identifier
        """
        super().__init__(feature_version)
        self.lag_hours = sorted(lag_hours)
        self.target_column = target_column
        self.station_id_column = station_id_column
        self.timestamp_column = timestamp_column

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate lag features

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with lag features added
        """
        logger.info(f"Generating lag features for {self.target_column}")

        # Validate input
        required_cols = [self.station_id_column, self.timestamp_column, self.target_column]
        if not self.validate_input(df, required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        original_cols = len(df.columns)
        df = df.copy()

        # Ensure timestamp is datetime and sorted
        df[self.timestamp_column] = pd.to_datetime(df[self.timestamp_column])
        df = df.sort_values([self.station_id_column, self.timestamp_column])

        # Generate lag features for each lag period
        for lag_hours in self.lag_hours:
            feature_name = f"{self.target_column}_lag_{lag_hours}h"

            # Group by station and shift
            df[feature_name] = df.groupby(self.station_id_column)[self.target_column].shift(lag_hours)

            self.feature_names.append(feature_name)

            logger.debug(f"Created lag feature: {feature_name}")

        # Calculate change/diff features
        for lag_hours in [1, 24]:  # Only for recent lags
            feature_name = f"{self.target_column}_change_{lag_hours}h"
            lag_col = f"{self.target_column}_lag_{lag_hours}h"

            if lag_col in df.columns:
                df[feature_name] = df[self.target_column] - df[lag_col]
                self.feature_names.append(feature_name)

        # Calculate percentage change
        for lag_hours in [1, 24]:
            feature_name = f"{self.target_column}_pct_change_{lag_hours}h"
            lag_col = f"{self.target_column}_lag_{lag_hours}h"

            if lag_col in df.columns:
                df[feature_name] = ((df[self.target_column] - df[lag_col]) / (df[lag_col] + 1)) * 100
                self.feature_names.append(feature_name)

        self.log_generation_summary(df, original_cols)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of generated feature names"""
        return self.feature_names


# Convenience function
def generate_lag_features(
    df: pd.DataFrame,
    lag_hours: List[int] = [1, 3, 6, 12, 24, 48, 168],
    target_column: str = "bikes_available",
    station_id_column: str = "station_id",
    timestamp_column: str = "timestamp"
) -> pd.DataFrame:
    """
    Generate lag features from DataFrame

    Args:
        df: Input DataFrame
        lag_hours: List of lag periods in hours
        target_column: Column to create lags for
        station_id_column: Station identifier column
        timestamp_column: Timestamp column

    Returns:
        DataFrame with lag features
    """
    generator = LagFeatureGenerator(
        lag_hours=lag_hours,
        target_column=target_column,
        station_id_column=station_id_column,
        timestamp_column=timestamp_column
    )
    return generator.generate(df)
