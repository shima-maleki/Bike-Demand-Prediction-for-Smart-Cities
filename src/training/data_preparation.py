"""
Data Preparation for ML Training
Handles feature retrieval, preprocessing, and splitting
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler

from src.utils.feature_store import feature_store
from src.config.settings import get_settings

settings = get_settings()


class DataPreparation:
    """Prepares data for ML model training"""

    def __init__(
        self,
        target_column: str = 'bikes_available',
        feature_version: str = 'v1.0',
        scaler_type: str = 'standard'
    ):
        """
        Initialize data preparation

        Args:
            target_column: Name of target variable
            feature_version: Version of features to use
            scaler_type: Type of scaler (standard, robust, minmax)
        """
        self.target_column = target_column
        self.feature_version = feature_version
        self.scaler_type = scaler_type
        self.scaler = None
        self.feature_columns = None

    def load_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Load data from feature store

        Args:
            start_date: Start date (default: days_back from now)
            end_date: End date (default: now)
            days_back: Days to look back if start_date not provided

        Returns:
            DataFrame with features and target
        """
        if end_date is None:
            end_date = datetime.utcnow()

        if start_date is None:
            start_date = end_date - timedelta(days=days_back)

        logger.info(f"Loading data from {start_date} to {end_date}")

        # Get data from feature store
        df = feature_store.get_training_data(
            start_date=start_date,
            end_date=end_date,
            include_target=True
        )

        if len(df) == 0:
            raise ValueError("No data retrieved from feature store")

        logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")

        return df

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess data for training

        Args:
            df: Input DataFrame

        Returns:
            Preprocessed DataFrame
        """
        logger.info("Preprocessing data")

        df = df.copy()

        # 1. Handle missing values
        df = self._handle_missing_values(df)

        # 2. Remove outliers
        df = self._remove_outliers(df)

        # 3. Ensure correct data types
        df = self._ensure_data_types(df)

        logger.info(f"After preprocessing: {len(df)} records")

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        logger.debug("Handling missing values")

        initial_rows = len(df)

        # For lag/rolling features, forward fill (time-series appropriate)
        lag_cols = [col for col in df.columns if 'lag_' in col or 'rolling_' in col]
        if lag_cols:
            df[lag_cols] = df.groupby('station_id')[lag_cols].ffill()

        # For other numeric columns, use median imputation
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col].fillna(median_val, inplace=True)

        # For categorical columns, use mode or 'unknown'
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if df[col].isnull().any():
                df[col].fillna('unknown', inplace=True)

        # Drop rows where target is missing
        df = df.dropna(subset=[self.target_column])

        logger.debug(f"Removed {initial_rows - len(df)} rows due to missing target")

        return df

    def _remove_outliers(self, df: pd.DataFrame, std_threshold: float = 3.0) -> pd.DataFrame:
        """Remove outliers using z-score method"""
        logger.debug("Removing outliers")

        initial_rows = len(df)

        # Only remove outliers from target variable
        if self.target_column in df.columns:
            z_scores = np.abs((df[self.target_column] - df[self.target_column].mean()) / df[self.target_column].std())
            df = df[z_scores < std_threshold]

        logger.debug(f"Removed {initial_rows - len(df)} outlier rows")

        return df

    def _ensure_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct data types"""
        logger.debug("Ensuring correct data types")

        # Convert categorical columns
        categorical_cols = ['season', 'part_of_day', 'temp_category', 'humidity_category',
                           'wind_category', 'rain_intensity', 'weather_condition']

        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype('category')

        return df

    def split_data(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Dict[str, pd.DataFrame]:
        """
        Split data into train/val/test sets (time-based split)

        Args:
            df: Input DataFrame
            train_ratio: Training data ratio
            val_ratio: Validation data ratio
            test_ratio: Test data ratio

        Returns:
            Dictionary with train, val, test DataFrames
        """
        splits = feature_store.prepare_for_training(
            df=df,
            target_column=self.target_column,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio
        )

        return splits

    def get_X_y(
        self,
        df: pd.DataFrame,
        scale_features: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Separate features and target

        Args:
            df: Input DataFrame
            scale_features: Whether to scale features

        Returns:
            Tuple of (X, y)
        """
        # Get feature columns
        if self.feature_columns is None:
            self.feature_columns = feature_store.get_feature_columns(df)

        # Ensure feature columns exist
        available_features = [col for col in self.feature_columns if col in df.columns]

        if len(available_features) < len(self.feature_columns):
            missing = set(self.feature_columns) - set(available_features)
            logger.warning(f"Missing {len(missing)} features: {list(missing)[:5]}...")

        self.feature_columns = available_features

        # Select only numeric features for now
        numeric_features = df[self.feature_columns].select_dtypes(include=[np.number]).columns.tolist()

        X = df[numeric_features].copy()
        y = df[self.target_column].copy()

        # Scale features if requested
        if scale_features:
            X = self._scale_features(X, fit=self.scaler is None)

        logger.info(f"Prepared X: {X.shape}, y: {y.shape}")

        return X, y

    def _scale_features(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Scale features using specified scaler

        Args:
            X: Features DataFrame
            fit: Whether to fit the scaler

        Returns:
            Scaled features DataFrame
        """
        if self.scaler is None:
            if self.scaler_type == 'standard':
                self.scaler = StandardScaler()
            elif self.scaler_type == 'robust':
                self.scaler = RobustScaler()
            elif self.scaler_type == 'minmax':
                self.scaler = MinMaxScaler()
            else:
                raise ValueError(f"Unknown scaler type: {self.scaler_type}")

        if fit:
            X_scaled = self.scaler.fit_transform(X)
            logger.debug(f"Fitted and transformed features using {self.scaler_type} scaler")
        else:
            X_scaled = self.scaler.transform(X)
            logger.debug(f"Transformed features using existing scaler")

        return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

    def prepare_training_data(
        self,
        days_back: int = 30,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Dict[str, Tuple[pd.DataFrame, pd.Series]]:
        """
        Complete data preparation pipeline

        Args:
            days_back: Days of historical data to load
            train_ratio: Training data ratio
            val_ratio: Validation data ratio
            test_ratio: Test data ratio

        Returns:
            Dictionary with train, val, test (X, y) tuples
        """
        logger.info("=== Starting Data Preparation Pipeline ===")

        # 1. Load data
        df = self.load_data(days_back=days_back)

        # 2. Preprocess
        df = self.preprocess(df)

        # 3. Split
        splits = self.split_data(df, train_ratio, val_ratio, test_ratio)

        # 4. Prepare X, y for each split
        X_train, y_train = self.get_X_y(splits['train'], scale_features=True)
        X_val, y_val = self.get_X_y(splits['val'], scale_features=True)
        X_test, y_test = self.get_X_y(splits['test'], scale_features=True)

        logger.info("=== Data Preparation Complete ===")

        return {
            'train': (X_train, y_train),
            'val': (X_val, y_val),
            'test': (X_test, y_test)
        }
