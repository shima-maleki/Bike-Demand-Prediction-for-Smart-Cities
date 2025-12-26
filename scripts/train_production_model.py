#!/usr/bin/env python3
"""
Train production model from historical features
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db_context
from sqlalchemy import text

# Set MLflow tracking URI
tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
mlflow.set_tracking_uri(tracking_uri)

logger.info("=" * 70)
logger.info("TRAINING PRODUCTION MODEL FROM HISTORICAL DATA")
logger.info("=" * 70)
logger.info(f"MLflow URI: {tracking_uri}")

# Fetch features from database
logger.info("Fetching features from database...")

with get_db_context() as db:
    features_df = pd.read_sql(
        text("""
            SELECT
                station_id,
                timestamp,
                feature_json
            FROM features
            WHERE feature_version = 'v1'
            ORDER BY timestamp
        """),
        db.connection()
    )

logger.info(f"Loaded {len(features_df)} feature records")

# Parse JSON features
logger.info("Parsing feature JSON...")

import json
features_list = []

for _, row in features_df.iterrows():
    # feature_json is already a dict (loaded as JSONB from PostgreSQL)
    feature_dict = row['feature_json'] if isinstance(row['feature_json'], dict) else json.loads(row['feature_json'])
    feature_dict['station_id'] = row['station_id']
    feature_dict['timestamp'] = row['timestamp']
    features_list.append(feature_dict)

df = pd.DataFrame(features_list)

logger.info(f"Parsed {len(df)} records with {len(df.columns)} columns")
logger.info(f"Columns: {list(df.columns)}")

# Prepare X and y
target_col = 'bikes_available'
exclude_cols = ['station_id', 'timestamp', target_col, 'docks_available']

feature_cols = [col for col in df.columns if col not in exclude_cols]

X = df[feature_cols]
y = df[target_col]

logger.info(f"Features shape: {X.shape}")
logger.info(f"Target shape: {y.shape}")

# Train/val/test split (70/15/15)
X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, random_state=42, shuffle=False)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.176, random_state=42, shuffle=False)

logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

# Set experiment
mlflow.set_experiment("bike-demand-production")

# Train XGBoost model
logger.info("=" * 70)
logger.info("Training XGBoost Model")
logger.info("=" * 70)

with mlflow.start_run(run_name="xgboost_production"):
    params = {
        'n_estimators': 200,
        'max_depth': 8,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }

    mlflow.log_params(params)

    model = XGBRegressor(**params)
    model.fit(X_train, y_train)

    # Evaluate
    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)

    val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
    val_mae = mean_absolute_error(y_val, val_pred)
    val_r2 = r2_score(y_val, val_pred)

    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
    test_mae = mean_absolute_error(y_test, test_pred)
    test_r2 = r2_score(y_test, test_pred)
    test_mape = np.mean(np.abs((y_test - test_pred) / (y_test + 1))) * 100

    metrics = {
        'val_rmse': val_rmse,
        'val_mae': val_mae,
        'val_r2': val_r2,
        'test_rmse': test_rmse,
        'test_mae': test_mae,
        'test_r2': test_r2,
        'test_mape': test_mape
    }

    mlflow.log_metrics(metrics)

    logger.info(f"Val RMSE: {val_rmse:.2f}, Val MAE: {val_mae:.2f}, Val R²: {val_r2:.4f}")
    logger.info(f"Test RMSE: {test_rmse:.2f}, Test MAE: {test_mae:.2f}, Test R²: {test_r2:.4f}")

    # Log model
    from mlflow.models.signature import infer_signature
    signature = infer_signature(X_train, model.predict(X_train))

    mlflow.sklearn.log_model(
        model,
        "model",
        registered_model_name="bike-demand-forecasting",
        signature=signature
    )

    xgb_run_id = mlflow.active_run().info.run_id
    xgb_rmse = test_rmse

logger.info(f"✓ XGBoost - Test RMSE: {xgb_rmse:.2f}")

# Train LightGBM model
logger.info("=" * 70)
logger.info("Training LightGBM Model")
logger.info("=" * 70)

with mlflow.start_run(run_name="lightgbm_production"):
    params = {
        'n_estimators': 200,
        'max_depth': 8,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbose': -1
    }

    mlflow.log_params(params)

    model = LGBMRegressor(**params)
    model.fit(X_train, y_train)

    # Evaluate
    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)

    val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
    val_mae = mean_absolute_error(y_val, val_pred)
    val_r2 = r2_score(y_val, val_pred)

    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
    test_mae = mean_absolute_error(y_test, test_pred)
    test_r2 = r2_score(y_test, test_pred)
    test_mape = np.mean(np.abs((y_test - test_pred) / (y_test + 1))) * 100

    metrics = {
        'val_rmse': val_rmse,
        'val_mae': val_mae,
        'val_r2': val_r2,
        'test_rmse': test_rmse,
        'test_mae': test_mae,
        'test_r2': test_r2,
        'test_mape': test_mape
    }

    mlflow.log_metrics(metrics)

    logger.info(f"Val RMSE: {val_rmse:.2f}, Val MAE: {val_mae:.2f}, Val R²: {val_r2:.4f}")
    logger.info(f"Test RMSE: {test_rmse:.2f}, Test MAE: {test_mae:.2f}, Test R²: {test_r2:.4f}")

    # Log model
    signature = infer_signature(X_train, model.predict(X_train))

    mlflow.sklearn.log_model(
        model,
        "model",
        registered_model_name="bike-demand-forecasting",
        signature=signature
    )

    lgb_run_id = mlflow.active_run().info.run_id
    lgb_rmse = test_rmse

logger.info(f"✓ LightGBM - Test RMSE: {lgb_rmse:.2f}")

# Determine best model
logger.info("=" * 70)
logger.info("MODEL COMPARISON")
logger.info("=" * 70)

best_model_name = "XGBoost" if xgb_rmse < lgb_rmse else "LightGBM"
best_rmse = min(xgb_rmse, lgb_rmse)

logger.info(f"Best Model: {best_model_name} (Test RMSE: {best_rmse:.2f})")

# Promote best model to Production
import time
time.sleep(3)

client = mlflow.tracking.MlflowClient()
model_name = "bike-demand-forecasting"

versions = client.search_model_versions(f"name='{model_name}'")

if versions:
    # Get the latest version
    latest_version = max([int(v.version) for v in versions])

    logger.info(f"Latest model version: {latest_version}")

    # Transition to Production
    client.transition_model_version_stage(
        name=model_name,
        version=latest_version,
        stage="Production",
        archive_existing_versions=True
    )

    logger.success(f"✅ Model version {latest_version} promoted to Production!")
    logger.info("=" * 70)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Best Model: {best_model_name}")
    logger.info(f"Test RMSE: {best_rmse:.2f} bikes")
    logger.info(f"MLflow UI: {tracking_uri}")
    logger.info(f"Model: {model_name} v{latest_version}")
    logger.info(f"Stage: Production")

else:
    logger.error("❌ No model versions found")
    sys.exit(1)
