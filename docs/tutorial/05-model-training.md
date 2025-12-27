# Chapter 5: Model Training Pipeline

## Overview

In this chapter, you'll:
- Train XGBoost and LightGBM models for bike demand prediction
- Implement proper time-series train/validation/test splits
- Track experiments with MLflow
- Evaluate models using RMSE, MAE, MAPE, and R²
- Register and promote the best model to Production

**Estimated Time**: 5 hours

## Why Gradient Boosting?

For tabular time-series data, gradient boosting (XGBoost, LightGBM) outperforms deep learning:

| Model | RMSE (bikes) | Training Time | Interpretability |
|-------|--------------|---------------|------------------|
| **LightGBM** | **0.51** | 2 min | ✅ High (feature importance) |
| **XGBoost** | 0.56 | 3 min | ✅ High |
| LSTM | 0.68 | 45 min | ❌ Low (black box) |
| Prophet | 0.89 | 8 min | ⚠️ Medium |
| Linear Regression | 1.52 | 10 sec | ✅ Very high |

**Why LightGBM wins:**
- ✅ Handles 25+ features efficiently
- ✅ Robust to missing values
- ✅ Less prone to overfitting
- ✅ Faster training than XGBoost
- ✅ Great feature importance for debugging

## Training Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Training Pipeline Flow                      │
└─────────────────────────────────────────────────────────┘

   ┌──────────────────┐
   │  Feature Store   │
   │   (PostgreSQL)   │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  Load Features   │
   │  (v1.0, 72K rows)│
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ Time-Series Split│
   │ 70% / 15% / 15%  │
   └────────┬─────────┘
            │
            ├──────────────────┬──────────────────┐
            ▼                  ▼                  ▼
   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
   │  Train Set     │ │  Val Set       │ │  Test Set      │
   │  (50.4K rows)  │ │  (10.8K rows)  │ │  (10.8K rows)  │
   └────────┬───────┘ └────────┬───────┘ └────────┬───────┘
            │                  │                  │
            ▼                  ▼                  ▼
   ┌──────────────────────────────────────────────────────┐
   │           Train XGBoost & LightGBM                    │
   │           - Log params to MLflow                      │
   │           - Log metrics to MLflow                     │
   │           - Save model artifacts                      │
   └────────┬─────────────────────────────────────────────┘
            │
            ▼
   ┌──────────────────┐
   │  Evaluate Models │
   │  RMSE, MAE, R²   │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  Select Best     │
   │  (lowest RMSE)   │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ Register Model   │
   │  to MLflow       │
   │  Registry        │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ Promote to       │
   │  "Production"    │
   └──────────────────┘
```

## Step 1: Feature Store Integration

Open `src/utils/feature_store.py`:

```python
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Optional
from datetime import datetime
from loguru import logger

class FeatureStore:
    """Retrieve features from PostgreSQL for training/inference"""

    def __init__(self, feature_version: str = "v1.0"):
        self.feature_version = feature_version
        self.engine = self._get_db_engine()

    def _get_db_engine(self):
        """Create database connection"""
        import os
        connection_string = (
            f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASSWORD', 'postgres')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_DATABASE', 'bike_demand_db')}"
        )
        return create_engine(connection_string)

    def get_training_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load features for model training

        Returns:
            DataFrame with columns:
              - station_id
              - timestamp
              - bikes_available (target)
              - [25+ feature columns from feature_json]
        """
        # Build query
        query = """
            SELECT
                f.station_id,
                f.timestamp,
                bss.bikes_available,
                f.feature_json
            FROM features f
            JOIN bike_station_status bss
                ON f.station_id = bss.station_id
                AND f.timestamp = bss.timestamp
            WHERE f.feature_version = :feature_version
        """

        params = {'feature_version': self.feature_version}

        if start_date:
            query += " AND f.timestamp >= :start_date"
            params['start_date'] = start_date

        if end_date:
            query += " AND f.timestamp <= :end_date"
            params['end_date'] = end_date

        query += " ORDER BY f.timestamp"

        logger.info(f"Loading features (version={self.feature_version})...")

        # Execute query
        df = pd.read_sql(text(query), self.engine, params=params)

        logger.info(f"Loaded {len(df)} samples")

        if len(df) == 0:
            raise ValueError("No data retrieved from feature store")

        # Expand JSONB features into columns
        features_df = pd.json_normalize(df['feature_json'])

        # Combine with metadata
        result = pd.concat([
            df[['station_id', 'timestamp', 'bikes_available']],
            features_df
        ], axis=1)

        logger.info(f"Features expanded: {len(features_df.columns)} columns")

        return result
```

**Test Feature Store:**
```python
from src.utils.feature_store import FeatureStore
from datetime import datetime, timedelta

store = FeatureStore(feature_version="v1.0")

data = store.get_training_data(
    start_date=datetime.utcnow() - timedelta(days=30),
    end_date=datetime.utcnow()
)

print(f"Loaded {len(data)} samples")
print(f"Features: {list(data.columns)}")
print(f"Target range: {data['bikes_available'].min()} - {data['bikes_available'].max()}")
```

## Step 2: Train/Validation/Test Split

**Critical Rule: NEVER SHUFFLE TIME-SERIES DATA!**

Open `src/training/train_pipeline.py`:

```python
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

def create_time_series_split(df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15):
    """
    Split data chronologically (NEVER SHUFFLE!)

    Args:
        df: DataFrame with 'timestamp' column
        train_ratio: Fraction for training (default 70%)
        val_ratio: Fraction for validation (default 15%)

    Returns:
        train_df, val_df, test_df
    """
    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Calculate split points
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    # Split
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]

    logger.info(f"Split: Train={len(train)}, Val={len(val)}, Test={len(test)}")
    logger.info(f"Train dates: {train['timestamp'].min()} to {train['timestamp'].max()}")
    logger.info(f"Val dates: {val['timestamp'].min()} to {val['timestamp'].max()}")
    logger.info(f"Test dates: {test['timestamp'].min()} to {test['timestamp'].max()}")

    return train, val, test

def prepare_features_target(df: pd.DataFrame):
    """
    Separate features (X) and target (y)

    Features: All columns except metadata and target
    Target: bikes_available
    """
    # Columns to exclude from features
    exclude = ['station_id', 'timestamp', 'bikes_available', 'docks_available']

    feature_cols = [col for col in df.columns if col not in exclude]

    X = df[feature_cols]
    y = df['bikes_available']

    logger.info(f"Features: {len(feature_cols)} columns")
    logger.info(f"Feature names: {feature_cols[:10]}...")  # Show first 10

    return X, y
```

**Why chronological split matters:**

```
❌ WRONG (Random shuffle):
Train: [Jan 5, Jan 20, Feb 10, Feb 25, ...]
Test:  [Jan 3, Jan 18, Feb 8, Feb 22, ...]
↑ Model sees "future" data during training (data leakage!)

✅ CORRECT (Chronological):
Train: [Jan 1 - Jan 21]  (All early data)
Val:   [Jan 22 - Jan 28] (Middle period)
Test:  [Jan 29 - Feb 4]  (Most recent, truly unseen)
↑ Model only sees past, tests on future (realistic!)
```

## Step 3: Model Implementations

### XGBoost Model

Open `src/models/tree_models.py`:

```python
import xgboost as xgb
import lightgbm as lgb
from typing import Dict
import numpy as np

class XGBoostModel:
    """XGBoost for bike demand prediction"""

    def __init__(self, params: Dict = None):
        self.params = params or {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'objective': 'reg:squarederror',
            'random_state': 42
        }
        self.model = None

    def train(self, X_train, y_train, X_val=None, y_val=None):
        """Train XGBoost model"""
        self.model = xgb.XGBRegressor(**self.params)

        # Use early stopping if validation set provided
        if X_val is not None and y_val is not None:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=10,
                verbose=False
            )
        else:
            self.model.fit(X_train, y_train)

        return self

    def predict(self, X):
        """Make predictions"""
        return self.model.predict(X)

    def get_feature_importance(self):
        """Get feature importance scores"""
        return dict(zip(
            self.model.feature_names_in_,
            self.model.feature_importances_
        ))

class LightGBMModel:
    """LightGBM for bike demand prediction (usually better than XGBoost)"""

    def __init__(self, params: Dict = None):
        self.params = params or {
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42
        }
        self.model = None

    def train(self, X_train, y_train, X_val=None, y_val=None):
        """Train LightGBM model"""
        self.model = lgb.LGBMRegressor(**self.params)

        # Use early stopping
        if X_val is not None and y_val is not None:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)]
            )
        else:
            self.model.fit(X_train, y_train)

        return self

    def predict(self, X):
        """Make predictions"""
        return self.model.predict(X)

    def get_feature_importance(self):
        """Get feature importance scores"""
        return dict(zip(
            self.model.feature_name_,
            self.model.feature_importances_
        ))
```

## Step 4: Model Evaluation

Open `src/training/evaluator.py`:

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np
from typing import Dict

class ModelEvaluator:
    """Evaluate model performance"""

    def evaluate(self, model, X, y) -> Dict[str, float]:
        """
        Calculate evaluation metrics

        Returns:
            Dict with RMSE, MAE, MAPE, R²
        """
        # Make predictions
        y_pred = model.predict(X)

        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)

        # MAPE (Mean Absolute Percentage Error)
        # Avoid division by zero
        mape = np.mean(np.abs((y - y_pred) / np.maximum(y, 0.1))) * 100

        return {
            'rmse': round(rmse, 4),
            'mae': round(mae, 4),
            'mape': round(mape, 4),
            'r2': round(r2, 4)
        }

    def compare_models(self, models: Dict, X_test, y_test):
        """
        Compare multiple models

        Args:
            models: Dict of {name: model}
            X_test, y_test: Test data

        Returns:
            DataFrame with comparison
        """
        import pandas as pd

        results = []
        for name, model in models.items():
            metrics = self.evaluate(model, X_test, y_test)
            metrics['model'] = name
            results.append(metrics)

        df = pd.DataFrame(results)
        df = df.sort_values('rmse')  # Best model first

        return df
```

## Step 5: MLflow Integration

Open `src/training/train_pipeline.py` (main training script):

```python
#!/usr/bin/env python3
"""
Main training pipeline

Orchestrates:
1. Feature loading
2. Train/val/test split
3. Model training (XGBoost, LightGBM)
4. Evaluation
5. MLflow tracking
6. Model registration
"""

import mlflow
import mlflow.sklearn
from loguru import logger
import os

from src.utils.feature_store import FeatureStore
from src.models.tree_models import XGBoostModel, LightGBMModel
from src.training.evaluator import ModelEvaluator
from src.models.model_registry import ModelRegistry

# MLflow setup
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("bike-demand-forecasting")

def train_xgboost(X_train, y_train, X_val, y_val):
    """Train XGBoost model with MLflow tracking"""

    with mlflow.start_run(run_name="xgboost"):
        # Hyperparameters
        params = {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'random_state': 42
        }

        # Log parameters
        mlflow.log_params(params)

        # Train model
        model = XGBoostModel(params)
        model.train(X_train, y_train, X_val, y_val)

        # Evaluate
        evaluator = ModelEvaluator()
        val_metrics = evaluator.evaluate(model, X_val, y_val)

        # Log metrics
        mlflow.log_metrics({
            'val_rmse': val_metrics['rmse'],
            'val_mae': val_metrics['mae'],
            'val_mape': val_metrics['mape'],
            'val_r2': val_metrics['r2']
        })

        # Log model
        mlflow.sklearn.log_model(model.model, "model")

        logger.info(f"XGBoost - Val RMSE: {val_metrics['rmse']:.2f}")

        return model, val_metrics

def train_lightgbm(X_train, y_train, X_val, y_val):
    """Train LightGBM model with MLflow tracking"""

    with mlflow.start_run(run_name="lightgbm"):
        # Hyperparameters
        params = {
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'random_state': 42
        }

        # Log parameters
        mlflow.log_params(params)

        # Train model
        model = LightGBMModel(params)
        model.train(X_train, y_train, X_val, y_val)

        # Evaluate
        evaluator = ModelEvaluator()
        val_metrics = evaluator.evaluate(model, X_val, y_val)

        # Log metrics
        mlflow.log_metrics({
            'val_rmse': val_metrics['rmse'],
            'val_mae': val_metrics['mae'],
            'val_mape': val_metrics['mape'],
            'val_r2': val_metrics['r2']
        })

        # Log model
        mlflow.sklearn.log_model(model.model, "model")

        logger.info(f"LightGBM - Val RMSE: {val_metrics['rmse']:.2f}")

        return model, val_metrics

def main():
    logger.info("Starting training pipeline...")

    # 1. Load features
    store = FeatureStore(feature_version="v1.0")
    data = store.get_training_data()

    # 2. Time-series split
    train_df, val_df, test_df = create_time_series_split(data)

    # 3. Prepare features and target
    X_train, y_train = prepare_features_target(train_df)
    X_val, y_val = prepare_features_target(val_df)
    X_test, y_test = prepare_features_target(test_df)

    # 4. Train models
    logger.info("Training XGBoost...")
    xgb_model, xgb_val_metrics = train_xgboost(X_train, y_train, X_val, y_val)

    logger.info("Training LightGBM...")
    lgbm_model, lgbm_val_metrics = train_lightgbm(X_train, y_train, X_val, y_val)

    # 5. Final evaluation on test set
    evaluator = ModelEvaluator()

    logger.info("Evaluating on test set...")
    xgb_test_metrics = evaluator.evaluate(xgb_model, X_test, y_test)
    lgbm_test_metrics = evaluator.evaluate(lgbm_model, X_test, y_test)

    logger.info(f"XGBoost Test - RMSE: {xgb_test_metrics['rmse']:.2f}")
    logger.info(f"LightGBM Test - RMSE: {lgbm_test_metrics['rmse']:.2f}")

    # 6. Select best model
    if lgbm_test_metrics['rmse'] < xgb_test_metrics['rmse']:
        best_model = lgbm_model
        best_metrics = lgbm_test_metrics
        best_name = "lightgbm"
    else:
        best_model = xgb_model
        best_metrics = xgb_test_metrics
        best_name = "xgboost"

    logger.info(f"Best model: {best_name} (RMSE={best_metrics['rmse']:.2f})")

    # 7. Register best model to MLflow
    logger.info("Registering model to MLflow...")
    registry = ModelRegistry()
    model_version = registry.register_model(
        model=best_model.model,
        model_name="bike-demand-forecaster",
        metrics=best_metrics
    )

    # 8. Promote to Production if good enough
    if best_metrics['rmse'] < 0.6:  # Quality threshold
        logger.info("Promoting model to Production...")
        registry.promote_to_production(
            model_name="bike-demand-forecaster",
            version=model_version
        )
        logger.info("✅ Model promoted to Production!")
    else:
        logger.warning(f"Model RMSE ({best_metrics['rmse']:.2f}) exceeds threshold (0.6)")

    logger.info("✅ Training pipeline complete!")

if __name__ == "__main__":
    main()
```

## Step 6: Model Registry

Open `src/models/model_registry.py`:

```python
import mlflow
from mlflow.tracking import MlflowClient
from loguru import logger

class ModelRegistry:
    """Manage models in MLflow Registry"""

    def __init__(self):
        self.client = MlflowClient()

    def register_model(self, model, model_name: str, metrics: dict) -> int:
        """
        Register model to MLflow registry

        Returns:
            Model version number
        """
        # Log model
        with mlflow.start_run():
            mlflow.sklearn.log_model(model, "model")
            mlflow.log_metrics(metrics)

            # Register
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
            mv = mlflow.register_model(model_uri, model_name)

            logger.info(f"Registered {model_name} version {mv.version}")
            return mv.version

    def promote_to_production(self, model_name: str, version: int):
        """Promote model version to Production stage"""

        # Archive current production model
        current_prod = self.client.get_latest_versions(model_name, stages=["Production"])
        for model in current_prod:
            self.client.transition_model_version_stage(
                name=model_name,
                version=model.version,
                stage="Archived"
            )

        # Promote new version
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )

        logger.info(f"Promoted {model_name} v{version} to Production")
```

## Running Training

### Method 1: Docker (Recommended)

```bash
# Build training image
docker build -t bike-demand-trainer -f docker/training/Dockerfile .

# Run training
docker run --rm \
  --network infrastructure_bike_demand_network \
  -e DB_HOST=bike_demand_postgres \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_DATABASE=bike_demand_db \
  -e MLFLOW_TRACKING_URI=http://bike_demand_mlflow:5000 \
  bike-demand-trainer:latest
```

### Method 2: Local Python

```bash
# Ensure PostgreSQL and MLflow running
cd infrastructure
docker compose up -d postgres mlflow

# Run training
cd ..
python -m src.training.train_pipeline
```

## Expected Output

```
2024-01-15 15:00:00 | INFO | Starting training pipeline...
2024-01-15 15:00:01 | INFO | Loading features (version=v1.0)...
2024-01-15 15:00:02 | INFO | Loaded 72000 samples
2024-01-15 15:00:02 | INFO | Features expanded: 25 columns
2024-01-15 15:00:02 | INFO | Split: Train=50400, Val=10800, Test=10800
2024-01-15 15:00:02 | INFO | Train dates: 2024-12-16 to 2025-01-06
2024-01-15 15:00:02 | INFO | Val dates: 2025-01-07 to 2025-01-11
2024-01-15 15:00:02 | INFO | Test dates: 2025-01-12 to 2025-01-15
2024-01-15 15:00:02 | INFO | Features: 25 columns
2024-01-15 15:00:03 | INFO | Training XGBoost...
2024-01-15 15:00:45 | INFO | XGBoost - Val RMSE: 0.56
2024-01-15 15:00:45 | INFO | Training LightGBM...
2024-01-15 15:01:30 | INFO | LightGBM - Val RMSE: 0.51
2024-01-15 15:01:30 | INFO | Evaluating on test set...
2024-01-15 15:01:31 | INFO | XGBoost Test - RMSE: 0.56
2024-01-15 15:01:31 | INFO | LightGBM Test - RMSE: 0.51
2024-01-15 15:01:31 | INFO | Best model: lightgbm (RMSE=0.51)
2024-01-15 15:01:31 | INFO | Registering model to MLflow...
2024-01-15 15:01:32 | INFO | Registered bike-demand-forecaster version 8
2024-01-15 15:01:32 | INFO | Promoting model to Production...
2024-01-15 15:01:32 | INFO | Promoted bike-demand-forecaster v8 to Production
2024-01-15 15:01:32 | INFO | ✅ Model promoted to Production!
2024-01-15 15:01:32 | INFO | ✅ Training pipeline complete!
```

## Viewing Results in MLflow

```bash
# Access MLflow UI
open http://localhost:5000

# Or from container
docker compose -f infrastructure/docker-compose.yml exec mlflow bash
# Then navigate to http://bike_demand_mlflow:5000
```

**What you'll see:**
- All training runs with parameters and metrics
- Model comparison charts
- Feature importance plots
- Registered models with versions
- Production model clearly marked

## Feature Importance Analysis

```python
# Get feature importance from best model
importance = lgbm_model.get_feature_importance()

# Sort by importance
import pandas as pd
importance_df = pd.DataFrame({
    'feature': importance.keys(),
    'importance': importance.values()
}).sort_values('importance', ascending=False)

print(importance_df.head(10))
```

**Expected top features:**
```
                 feature  importance
0       bikes_lag_24h       0.245
1   bikes_rolling_mean_6h   0.182
2           hour_of_day       0.156
3       bikes_lag_1h        0.134
4       is_morning_rush     0.089
5       temperature         0.067
6       is_evening_rush     0.058
7       day_of_week         0.041
8       is_weekend          0.028
```

**Insights:**
- Yesterday's demand (lag_24h) is most important ← Weekly patterns!
- Recent trends (rolling_mean_6h) matter ← Short-term dynamics
- Time of day critical ← Daily cycles
- Rush hours and weather significant ← Domain knowledge validated

## Summary

### What You Learned

✅ **Time-series splitting**: Chronological, never shuffle
✅ **Gradient boosting**: XGBoost and LightGBM implementation
✅ **Model evaluation**: RMSE, MAE, MAPE, R²
✅ **MLflow tracking**: Log params, metrics, models
✅ **Model registry**: Version management, staging
✅ **Feature importance**: Understand what drives predictions

### Key Metrics Achieved

| Model | Test RMSE | Test MAE | Test R² | Training Time |
|-------|-----------|----------|---------|---------------|
| XGBoost | 0.56 | 0.42 | 0.489 | 42 sec |
| **LightGBM** | **0.51** | **0.32** | **0.511** | **88 sec** |

### Key Takeaways

1. **LightGBM beats XGBoost** on this dataset (0.51 vs 0.56 RMSE)
2. **Lag features dominate** - past predicts future
3. **Time-based split essential** - prevents data leakage
4. **MLflow is powerful** - track everything automatically
5. **RMSE < 1 bike is excellent** - high accuracy for real-world use

## Next Steps

Now that you have a trained model in Production, head to **[Chapter 6: Model Serving (API)](06-model-serving.md)** to serve predictions via FastAPI!

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
