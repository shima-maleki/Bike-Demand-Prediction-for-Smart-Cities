"""
ML Training Pipeline
End-to-end pipeline from feature store to trained model
"""

import mlflow
import mlflow.sklearn
import mlflow.xgboost
from typing import Dict, Any, Tuple
from loguru import logger
import pandas as pd
import numpy as np

from src.training.data_preparation import DataPreparation
from src.config.settings import get_settings

settings = get_settings()


class TrainingPipeline:
    """End-to-end ML training pipeline"""

    def __init__(
        self,
        experiment_name: str = "bike_demand_forecasting",
        model_type: str = "xgboost"
    ):
        """
        Initialize training pipeline

        Args:
            experiment_name: MLflow experiment name
            model_type: Type of model to train
        """
        self.experiment_name = experiment_name
        self.model_type = model_type

        # Set MLflow tracking URI
        mlflow.set_tracking_uri(settings.mlflow.tracking_uri)
        mlflow.set_experiment(experiment_name)

    def run(
        self,
        days_back: int = 30,
        hyperparameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        
        """
        Run complete training pipeline

        Args:
            days_back: Days of historical data
            hyperparameters: Model hyperparameters

        Returns:
            Dictionary with training results
        """
        logger.info("=" * 70)
        logger.info("STARTING ML TRAINING PIPELINE")
        logger.info("=" * 70)

        with mlflow.start_run() as run:
            # Log run info
            logger.info(f"MLflow Run ID: {run.info.run_id}")

            # Step 1: Prepare data
            logger.info("\n[1/4] Data Preparation")
            data_prep = DataPreparation()
            data = data_prep.prepare_training_data(days_back=days_back)

            X_train, y_train = data['train']
            X_val, y_val = data['val']
            X_test, y_test = data['test']

            # Log data info
            mlflow.log_param("train_size", len(X_train))
            mlflow.log_param("val_size", len(X_val))
            mlflow.log_param("test_size", len(X_test))
            mlflow.log_param("num_features", X_train.shape[1])

            # Step 2: Train model
            logger.info("\n[2/4] Model Training")
            model = self._train_model(X_train, y_train, hyperparameters)

            # Step 3: Evaluate model
            logger.info("\n[3/4] Model Evaluation")
            metrics = self._evaluate_model(model, X_val, y_val, X_test, y_test)

            # Step 4: Log to MLflow
            logger.info("\n[4/4] Logging to MLflow")
            self._log_to_mlflow(model, metrics, hyperparameters)

            logger.info("\n" + "=" * 70)
            logger.info("TRAINING PIPELINE COMPLETE")
            logger.info("=" * 70)

            return {
                'run_id': run.info.run_id,
                'model': model,
                'metrics': metrics
            }

    def _train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparameters: Dict[str, Any] = None
    ):
        """Train model based on model_type"""
        logger.info(f"Training {self.model_type} model...")

        if hyperparameters is None:
            hyperparameters = self._get_default_hyperparameters()

        if self.model_type == "xgboost":
            from xgboost import XGBRegressor
            model = XGBRegressor(**hyperparameters)

        elif self.model_type == "lightgbm":
            from lightgbm import LGBMRegressor
            model = LGBMRegressor(**hyperparameters)

        elif self.model_type == "catboost":
            from catboost import CatBoostRegressor
            model = CatBoostRegressor(**hyperparameters, verbose=False)

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

        # Train
        model.fit(X_train, y_train)

        logger.info(f"✓ {self.model_type} model trained successfully")

        return model

    def _evaluate_model(
        self,
        model,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """Evaluate model on validation and test sets"""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        # Validation metrics
        y_val_pred = model.predict(X_val)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        val_mae = mean_absolute_error(y_val, y_val_pred)
        val_mape = np.mean(np.abs((y_val - y_val_pred) / (y_val + 1))) * 100
        val_r2 = r2_score(y_val, y_val_pred)

        # Test metrics
        y_test_pred = model.predict(X_test)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        test_mae = mean_absolute_error(y_test, y_test_pred)
        test_mape = np.mean(np.abs((y_test - y_test_pred) / (y_test + 1))) * 100
        test_r2 = r2_score(y_test, y_test_pred)

        metrics = {
            'val_rmse': val_rmse,
            'val_mae': val_mae,
            'val_mape': val_mape,
            'val_r2': val_r2,
            'test_rmse': test_rmse,
            'test_mae': test_mae,
            'test_mape': test_mape,
            'test_r2': test_r2
        }

        logger.info("Validation Metrics:")
        logger.info(f"  RMSE: {val_rmse:.2f}")
        logger.info(f"  MAE:  {val_mae:.2f}")
        logger.info(f"  MAPE: {val_mape:.2f}%")
        logger.info(f"  R²:   {val_r2:.4f}")

        logger.info("Test Metrics:")
        logger.info(f"  RMSE: {test_rmse:.2f}")
        logger.info(f"  MAE:  {test_mae:.2f}")
        logger.info(f"  MAPE: {test_mape:.2f}%")
        logger.info(f"  R²:   {test_r2:.4f}")

        return metrics

    def _log_to_mlflow(
        self,
        model,
        metrics: Dict[str, float],
        hyperparameters: Dict[str, Any]
    ):
        """Log model, metrics, and parameters to MLflow"""
        # Log parameters
        if hyperparameters:
            for key, value in hyperparameters.items():
                mlflow.log_param(key, value)

        # Log metrics
        for key, value in metrics.items():
            mlflow.log_metric(key, value)

        # Log model
        if self.model_type in ["xgboost", "lightgbm"]:
            mlflow.sklearn.log_model(model, "model")
        else:
            mlflow.sklearn.log_model(model, "model")

        logger.info("✓ Logged to MLflow successfully")

    def _get_default_hyperparameters(self) -> Dict[str, Any]:
        """Get default hyperparameters for model"""
        defaults = {
            "xgboost": {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42
            },
            "lightgbm": {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42
            },
            "catboost": {
                "iterations": 100,
                "depth": 6,
                "learning_rate": 0.1,
                "random_state": 42
            }
        }

        return defaults.get(self.model_type, {})


def train_model(
    model_type: str = "xgboost",
    days_back: int = 30,
    hyperparameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convenience function to train a model

    Args:
        model_type: Type of model (xgboost, lightgbm, catboost)
        days_back: Days of historical data
        hyperparameters: Model hyperparameters

    Returns:
        Training results
    """
    pipeline = TrainingPipeline(model_type=model_type)
    return pipeline.run(days_back=days_back, hyperparameters=hyperparameters)


if __name__ == "__main__":
    """
    Production training script - trains multiple models and promotes best to Production
    Run with: python -m src.training.train_pipeline
    """
    logger.info("=" * 70)
    logger.info("PRODUCTION MODEL TRAINING")
    logger.info("=" * 70)
    logger.info(f"MLflow URI: {settings.mlflow.tracking_uri}")
    logger.info("")

    # Train XGBoost
    logger.info("Training XGBoost Model...")
    xgb_result = train_model(
        model_type="xgboost",
        days_back=30,
        hyperparameters={
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
    )
    logger.info(f"✓ XGBoost - Test RMSE: {xgb_result['metrics']['test_rmse']:.2f}")
    logger.info("")

    # Train LightGBM
    logger.info("Training LightGBM Model...")
    lgb_result = train_model(
        model_type="lightgbm",
        days_back=30,
        hyperparameters={
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1,
            'num_leaves': 31,
            'min_child_samples': 20,
            'random_state': 42,
            'verbose': -1
        }
    )
    logger.info(f"✓ LightGBM - Test RMSE: {lgb_result['metrics']['test_rmse']:.2f}")
    logger.info("")

    # Compare models and promote best
    logger.info("=" * 70)
    logger.info("MODEL COMPARISON")
    logger.info("=" * 70)

    xgb_rmse = xgb_result['metrics']['test_rmse']
    lgb_rmse = lgb_result['metrics']['test_rmse']

    if lgb_rmse < xgb_rmse:
        best_model = "LightGBM"
        best_run_id = lgb_result['run_id']
        best_rmse = lgb_rmse
    else:
        best_model = "XGBoost"
        best_run_id = xgb_result['run_id']
        best_rmse = xgb_rmse

    logger.info(f"Best Model: {best_model} (Test RMSE: {best_rmse:.2f})")

    # Register and promote model to Production
    client = mlflow.tracking.MlflowClient()

    # Get model URI from the best run
    model_uri = f"runs:/{best_run_id}/model"

    # Register model
    model_name = "bike-demand-forecasting"
    model_version = mlflow.register_model(model_uri, model_name)

    logger.info(f"Latest model version: {model_version.version}")

    # Promote to Production
    client.transition_model_version_stage(
        name=model_name,
        version=model_version.version,
        stage="Production",
        archive_existing_versions=True
    )

    logger.success(f"✅ Model version {model_version.version} promoted to Production!")

    logger.info("=" * 70)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Best Model: {best_model}")
    logger.info(f"Test RMSE: {best_rmse:.2f} bikes")
    logger.info(f"MLflow UI: {settings.mlflow.tracking_uri}")
    logger.info(f"Model: {model_name} v{model_version.version}")
    logger.info(f"Stage: Production")
