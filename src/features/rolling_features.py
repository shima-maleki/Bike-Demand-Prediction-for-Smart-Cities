"""
Rolling Window Feature Engineering
Generates rolling statistics for time-series forecasting
"""

import pandas as pd
from typing import List
from loguru import logger

from src.features.base_features import BaseFeatureGenerator


class RollingFeatureGenerator(BaseFeatureGenerator):
    """Generator for rolling window features"""

    def __init__(
        self,
        windows: List[int] = [3, 6, 12, 24],
        statistics: List[str] = ["mean", "std", "min", "max"],
        target_column: str = "bikes_available",
        station_id_column: str = "station_id",
        timestamp_column: str = "timestamp",
        feature_version: str = "v1.0"
    ):
        """
        Initialize rolling feature generator

        Args:
            windows: List of window sizes in hours
            statistics: List of statistics to calculate (mean, std, min, max, median)
            target_column: Column to calculate rolling stats for
            station_id_column: Station identifier column
            timestamp_column: Timestamp column
            feature_version: Version identifier
        """
        super().__init__(feature_version)
        self.windows = sorted(windows)
        self.statistics = statistics
        self.target_column = target_column
        self.station_id_column = station_id_column
        self.timestamp_column = timestamp_column

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate rolling window features

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with rolling features added
        """
        logger.info(f"Generating rolling features for {self.target_column}")

        # Validate input
        required_cols = [self.station_id_column, self.timestamp_column, self.target_column]
        if not self.validate_input(df, required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        original_cols = len(df.columns)
        df = df.copy()

        # Ensure timestamp is datetime and sorted
        df[self.timestamp_column] = pd.to_datetime(df[self.timestamp_column])
        df = df.sort_values([self.station_id_column, self.timestamp_column])

        # Generate rolling features for each window and statistic
        for window in self.windows:
            for stat in self.statistics:
                feature_name = f"{self.target_column}_rolling_{stat}_{window}h"

                # Group by station and calculate rolling statistic
                df[feature_name] = (
                    df.groupby(self.station_id_column)[self.target_column]
                    .rolling(window=window, min_periods=1)
                    .agg(stat)
                    .reset_index(level=0, drop=True)
                )

                self.feature_names.append(feature_name)

                logger.debug(f"Created rolling feature: {feature_name}")

        # Additional derived rolling features
        for window in [3, 24]:  # Only for selected windows
            # Range (max - min)
            max_col = f"{self.target_column}_rolling_max_{window}h"
            min_col = f"{self.target_column}_rolling_min_{window}h"

            if max_col in df.columns and min_col in df.columns:
                feature_name = f"{self.target_column}_rolling_range_{window}h"
                df[feature_name] = df[max_col] - df[min_col]
                self.feature_names.append(feature_name)

            # Coefficient of variation (std / mean)
            mean_col = f"{self.target_column}_rolling_mean_{window}h"
            std_col = f"{self.target_column}_rolling_std_{window}h"

            if mean_col in df.columns and std_col in df.columns:
                feature_name = f"{self.target_column}_rolling_cv_{window}h"
                df[feature_name] = df[std_col] / (df[mean_col] + 1)  # +1 to avoid division by zero
                self.feature_names.append(feature_name)

        self.log_generation_summary(df, original_cols)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of generated feature names"""
        return self.feature_names


# Convenience function
def generate_rolling_features(
    df: pd.DataFrame,
    windows: List[int] = [3, 6, 12, 24],
    statistics: List[str] = ["mean", "std", "min", "max"],
    target_column: str = "bikes_available",
    station_id_column: str = "station_id",
    timestamp_column: str = "timestamp"
) -> pd.DataFrame:
    """
    Generate rolling window features from DataFrame

    Args:
        df: Input DataFrame
        windows: List of window sizes in hours
        statistics: List of statistics to calculate
        target_column: Column to calculate rolling stats for
        station_id_column: Station identifier column
        timestamp_column: Timestamp column

    Returns:
        DataFrame with rolling features
    """
    generator = RollingFeatureGenerator(
        windows=windows,
        statistics=statistics,
        target_column=target_column,
        station_id_column=station_id_column,
        timestamp_column=timestamp_column
    )
    return generator.generate(df)
