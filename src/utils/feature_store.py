"""
Feature Store Interface
Retrieves engineered features for ML training
"""

import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_

from src.config.database import get_db_context
from src.data.models import Feature, BikeStationStatus


class FeatureStore:
    """Interface for retrieving features for ML training"""

    def __init__(self, feature_version: str = "v1.0"):
        """
        Initialize feature store

        Args:
            feature_version: Version of features to retrieve
        """
        self.feature_version = feature_version

    def get_training_data(
        self,
        start_date: datetime,
        end_date: datetime,
        station_ids: Optional[List[str]] = None,
        include_target: bool = True
    ) -> pd.DataFrame:
        """
        Get training data with features and target variable

        Args:
            start_date: Start date for data
            end_date: End date for data
            station_ids: Optional list of station IDs to filter
            include_target: Whether to include target variable

        Returns:
            DataFrame with features and optional target
        """
        logger.info(f"Retrieving training data from {start_date} to {end_date}")

        with get_db_context() as db:
            # Query features
            feature_query = select(Feature).where(
                and_(
                    Feature.timestamp >= start_date,
                    Feature.timestamp <= end_date,
                    Feature.feature_version == self.feature_version
                )
            )

            if station_ids:
                feature_query = feature_query.where(Feature.station_id.in_(station_ids))

            features_df = pd.read_sql(feature_query, db.connection())

            if len(features_df) == 0:
                logger.warning("No features found for specified criteria")
                return pd.DataFrame()

            # Expand JSONB features into columns
            features_expanded = self._expand_feature_json(features_df)

            # Include target variable if requested
            if include_target:
                status_query = select(BikeStationStatus).where(
                    and_(
                        BikeStationStatus.timestamp >= start_date,
                        BikeStationStatus.timestamp <= end_date
                    )
                )

                if station_ids:
                    status_query = status_query.where(BikeStationStatus.station_id.in_(station_ids))

                status_df = pd.read_sql(status_query, db.connection())

                logger.debug(f"Status DF shape: {status_df.shape}, columns: {list(status_df.columns)}")
                logger.debug(f"Features expanded shape: {features_expanded.shape}")

                # Check if bikes_available exists
                if 'bikes_available' not in status_df.columns:
                    logger.error(f"bikes_available not in status_df! Columns: {list(status_df.columns)}")
                    raise ValueError("bikes_available column missing from bike_station_status query")

                # Drop bikes_available from features if it exists (it will be from feature JSON)
                # We want to use the actual bikes_available from bike_station_status table
                if 'bikes_available' in features_expanded.columns:
                    logger.debug("Dropping bikes_available from features (will use from status table)")
                    features_expanded = features_expanded.drop(columns=['bikes_available'])

                # Also drop docks_available from features if it exists
                if 'docks_available' in features_expanded.columns:
                    features_expanded = features_expanded.drop(columns=['docks_available'])

                # Merge features with target
                merged_df = pd.merge(
                    features_expanded,
                    status_df[['station_id', 'timestamp', 'bikes_available']],
                    on=['station_id', 'timestamp'],
                    how='left'
                )

                logger.debug(f"Merged DF shape: {merged_df.shape}, has bikes_available: {'bikes_available' in merged_df.columns}")
                if 'bikes_available' in merged_df.columns:
                    logger.debug(f"bikes_available null count: {merged_df['bikes_available'].isnull().sum()}")

                logger.info(f"Retrieved {len(merged_df)} records with {len(merged_df.columns)} features")
                return merged_df
            else:
                logger.info(f"Retrieved {len(features_expanded)} records with {len(features_expanded.columns)} features")
                return features_expanded

    def _expand_feature_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expand JSONB feature column into separate columns

        Args:
            df: DataFrame with feature_json column

        Returns:
            DataFrame with expanded features
        """
        logger.debug("Expanding JSONB features")

        if 'feature_json' not in df.columns:
            return df

        # Extract base columns
        base_df = df[['id', 'station_id', 'timestamp', 'feature_version']].copy()

        # Expand JSONB into flat structure
        feature_dicts = df['feature_json'].apply(lambda x: self._flatten_dict(x))
        feature_df = pd.DataFrame(feature_dicts.tolist())

        # Combine
        result = pd.concat([base_df, feature_df], axis=1)

        logger.debug(f"Expanded {len(feature_df.columns)} features from JSONB")

        return result

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        Flatten nested dictionary

        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def prepare_for_training(
        self,
        df: pd.DataFrame,
        target_column: str = 'bikes_available',
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Dict[str, pd.DataFrame]:
        """
        Prepare data for ML training with time-based split

        Args:
            df: Input DataFrame
            target_column: Name of target column
            train_ratio: Training data ratio
            val_ratio: Validation data ratio
            test_ratio: Test data ratio

        Returns:
            Dictionary with train, val, test DataFrames
        """
        logger.info("Preparing data for training")

        # Sort by timestamp (critical for time-series)
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate split indices
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        # Time-based split (no shuffling!)
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

        logger.info(f"Data split:")
        logger.info(f"  Training:   {len(train_df)} records ({train_ratio*100:.1f}%)")
        logger.info(f"  Validation: {len(val_df)} records ({val_ratio*100:.1f}%)")
        logger.info(f"  Test:       {len(test_df)} records ({test_ratio*100:.1f}%)")

        return {
            'train': train_df,
            'val': val_df,
            'test': test_df
        }

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Get list of feature columns (excluding metadata)

        Args:
            df: DataFrame

        Returns:
            List of feature column names
        """
        exclude_cols = [
            'id', 'station_id', 'timestamp', 'feature_version',
            'bikes_available', 'docks_available', 'created_at'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"Found {len(feature_cols)} feature columns")

        return feature_cols


# Singleton instance
feature_store = FeatureStore()
