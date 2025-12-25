"""
Model Training DAG
Trains bike demand forecasting models daily using engineered features
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from loguru import logger
import mlflow
from typing import Dict, Any

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.training.train_pipeline import TrainingPipeline
from src.config.settings import get_settings

settings = get_settings()


default_args = {
    "owner": "bike-demand-prediction",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=2),
}


def validate_feature_availability(**context):
    """
    Task: Validate that sufficient features exist for training

    Returns:
        dict: Feature availability summary
    """
    logger.info("Validating feature availability")

    try:
        from src.config.database import get_db_context
        from sqlalchemy import select, func
        from src.data.models import Feature

        with get_db_context() as db:
            # Check feature count
            feature_count = db.query(func.count(Feature.id)).scalar()

            # Check date range
            oldest_feature = db.query(func.min(Feature.timestamp)).scalar()
            newest_feature = db.query(func.max(Feature.timestamp)).scalar()

            logger.info(f"Total feature records: {feature_count}")
            logger.info(f"Date range: {oldest_feature} to {newest_feature}")

            if feature_count < 100:
                raise ValueError(f"Insufficient features for training: {feature_count} < 100")

            # Push to XCom
            context["ti"].xcom_push(key="feature_count", value=feature_count)
            context["ti"].xcom_push(key="oldest_feature", value=str(oldest_feature))
            context["ti"].xcom_push(key="newest_feature", value=str(newest_feature))

            return {
                "feature_count": feature_count,
                "oldest": str(oldest_feature),
                "newest": str(newest_feature)
            }

    except Exception as e:
        logger.error(f"Feature validation failed: {e}")
        raise


def train_xgboost_model(**context):
    """
    Task: Train XGBoost model

    Returns:
        dict: Training results
    """
    logger.info("Training XGBoost model")

    try:
        pipeline = TrainingPipeline(
            experiment_name="bike_demand_forecasting",
            model_type="xgboost"
        )

        hyperparameters = {
            "n_estimators": 200,
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "gamma": 0.1,
            "random_state": 42
        }

        results = pipeline.run(
            days_back=30,
            hyperparameters=hyperparameters
        )

        # Push results to XCom
        context["ti"].xcom_push(key="xgboost_run_id", value=results["run_id"])
        context["ti"].xcom_push(key="xgboost_test_rmse", value=results["metrics"]["test_rmse"])
        context["ti"].xcom_push(key="xgboost_test_mape", value=results["metrics"]["test_mape"])

        logger.info(f"XGBoost training complete. Run ID: {results['run_id']}")
        logger.info(f"Test RMSE: {results['metrics']['test_rmse']:.2f}")
        logger.info(f"Test MAPE: {results['metrics']['test_mape']:.2f}%")

        return {
            "run_id": results["run_id"],
            "test_rmse": results["metrics"]["test_rmse"],
            "test_mape": results["metrics"]["test_mape"]
        }

    except Exception as e:
        logger.error(f"XGBoost training failed: {e}")
        raise


def train_lightgbm_model(**context):
    """
    Task: Train LightGBM model

    Returns:
        dict: Training results
    """
    logger.info("Training LightGBM model")

    try:
        pipeline = TrainingPipeline(
            experiment_name="bike_demand_forecasting",
            model_type="lightgbm"
        )

        hyperparameters = {
            "n_estimators": 200,
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 0.1,
            "random_state": 42
        }

        results = pipeline.run(
            days_back=30,
            hyperparameters=hyperparameters
        )

        # Push results to XCom
        context["ti"].xcom_push(key="lightgbm_run_id", value=results["run_id"])
        context["ti"].xcom_push(key="lightgbm_test_rmse", value=results["metrics"]["test_rmse"])
        context["ti"].xcom_push(key="lightgbm_test_mape", value=results["metrics"]["test_mape"])

        logger.info(f"LightGBM training complete. Run ID: {results['run_id']}")
        logger.info(f"Test RMSE: {results['metrics']['test_rmse']:.2f}")
        logger.info(f"Test MAPE: {results['metrics']['test_mape']:.2f}%")

        return {
            "run_id": results["run_id"],
            "test_rmse": results["metrics"]["test_rmse"],
            "test_mape": results["metrics"]["test_mape"]
        }

    except Exception as e:
        logger.error(f"LightGBM training failed: {e}")
        raise


def train_catboost_model(**context):
    """
    Task: Train CatBoost model

    Returns:
        dict: Training results
    """
    logger.info("Training CatBoost model")

    try:
        pipeline = TrainingPipeline(
            experiment_name="bike_demand_forecasting",
            model_type="catboost"
        )

        hyperparameters = {
            "iterations": 200,
            "depth": 8,
            "learning_rate": 0.05,
            "l2_leaf_reg": 3,
            "random_state": 42
        }

        results = pipeline.run(
            days_back=30,
            hyperparameters=hyperparameters
        )

        # Push results to XCom
        context["ti"].xcom_push(key="catboost_run_id", value=results["run_id"])
        context["ti"].xcom_push(key="catboost_test_rmse", value=results["metrics"]["test_rmse"])
        context["ti"].xcom_push(key="catboost_test_mape", value=results["metrics"]["test_mape"])

        logger.info(f"CatBoost training complete. Run ID: {results['run_id']}")
        logger.info(f"Test RMSE: {results['metrics']['test_rmse']:.2f}")
        logger.info(f"Test MAPE: {results['metrics']['test_mape']:.2f}%")

        return {
            "run_id": results["run_id"],
            "test_rmse": results["metrics"]["test_rmse"],
            "test_mape": results["metrics"]["test_mape"]
        }

    except Exception as e:
        logger.error(f"CatBoost training failed: {e}")
        raise


def compare_models_and_register_best(**context):
    """
    Task: Compare all trained models and register the best one to MLflow model registry

    Returns:
        dict: Best model information
    """
    logger.info("Comparing models and registering best model")

    try:
        ti = context["ti"]

        # Get results from all models
        models = {
            "xgboost": {
                "run_id": ti.xcom_pull(key="xgboost_run_id", task_ids="train_xgboost"),
                "test_rmse": ti.xcom_pull(key="xgboost_test_rmse", task_ids="train_xgboost"),
                "test_mape": ti.xcom_pull(key="xgboost_test_mape", task_ids="train_xgboost"),
            },
            "lightgbm": {
                "run_id": ti.xcom_pull(key="lightgbm_run_id", task_ids="train_lightgbm"),
                "test_rmse": ti.xcom_pull(key="lightgbm_test_rmse", task_ids="train_lightgbm"),
                "test_mape": ti.xcom_pull(key="lightgbm_test_mape", task_ids="train_lightgbm"),
            },
            "catboost": {
                "run_id": ti.xcom_pull(key="catboost_run_id", task_ids="train_catboost"),
                "test_rmse": ti.xcom_pull(key="catboost_test_rmse", task_ids="train_catboost"),
                "test_mape": ti.xcom_pull(key="catboost_test_mape", task_ids="train_catboost"),
            }
        }

        # Find best model by test RMSE
        best_model_name = min(models.keys(), key=lambda k: models[k]["test_rmse"])
        best_model_info = models[best_model_name]

        logger.info("=" * 70)
        logger.info("MODEL COMPARISON RESULTS")
        logger.info("=" * 70)

        for model_name, info in models.items():
            marker = "🏆" if model_name == best_model_name else "  "
            logger.info(f"{marker} {model_name.upper()}:")
            logger.info(f"   RMSE: {info['test_rmse']:.2f}")
            logger.info(f"   MAPE: {info['test_mape']:.2f}%")
            logger.info(f"   Run ID: {info['run_id']}")

        logger.info("=" * 70)
        logger.info(f"Best Model: {best_model_name.upper()}")
        logger.info(f"Best RMSE: {best_model_info['test_rmse']:.2f}")
        logger.info("=" * 70)

        # Register best model to MLflow Model Registry
        mlflow.set_tracking_uri(settings.mlflow.tracking_uri)

        model_name = "bike-demand-forecasting"
        model_uri = f"runs:/{best_model_info['run_id']}/model"

        # Register model
        model_version = mlflow.register_model(
            model_uri=model_uri,
            name=model_name
        )

        logger.info(f"✓ Registered {best_model_name} as '{model_name}' version {model_version.version}")

        # Transition to production if RMSE is acceptable (< 10 bikes)
        client = mlflow.tracking.MlflowClient()

        if best_model_info["test_rmse"] < 10:
            client.transition_model_version_stage(
                name=model_name,
                version=model_version.version,
                stage="Production"
            )
            logger.info(f"✓ Transitioned model version {model_version.version} to Production")
        else:
            logger.warning(f"Model RMSE ({best_model_info['test_rmse']:.2f}) > 10, keeping in Staging")

        # Store performance in database
        from src.config.database import get_db_context
        from src.data.models import ModelPerformance

        with get_db_context() as db:
            for model_type, info in models.items():
                performance = ModelPerformance(
                    model_name=model_type,
                    model_version=f"v{datetime.utcnow().strftime('%Y%m%d')}",
                    evaluation_date=datetime.utcnow(),
                    rmse=info["test_rmse"],
                    mae=0.0,  # Would be pulled from MLflow
                    mape=info["test_mape"],
                    r2_score=0.0,  # Would be pulled from MLflow
                    data_drift_score=None
                )
                db.add(performance)

            db.commit()

        logger.info("✓ Stored model performance metrics in database")

        return {
            "best_model": best_model_name,
            "best_rmse": best_model_info["test_rmse"],
            "best_mape": best_model_info["test_mape"],
            "model_version": model_version.version
        }

    except Exception as e:
        logger.error(f"Model comparison failed: {e}")
        raise


def cleanup_old_models(**context):
    """
    Task: Clean up old models from MLflow to save storage

    Returns:
        int: Number of models archived
    """
    logger.info("Cleaning up old models")

    try:
        mlflow.set_tracking_uri(settings.mlflow.tracking_uri)
        client = mlflow.tracking.MlflowClient()

        model_name = "bike-demand-forecasting"

        # Get all versions
        versions = client.search_model_versions(f"name='{model_name}'")

        archived_count = 0

        # Archive versions older than 30 days that are not in Production/Staging
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        for version in versions:
            # Skip if in Production or Staging
            if version.current_stage in ["Production", "Staging"]:
                continue

            # Check creation time
            creation_time = datetime.fromtimestamp(version.creation_timestamp / 1000)

            if creation_time < cutoff_date:
                client.transition_model_version_stage(
                    name=model_name,
                    version=version.version,
                    stage="Archived"
                )
                archived_count += 1
                logger.info(f"Archived model version {version.version} (created {creation_time})")

        logger.info(f"✓ Archived {archived_count} old model versions")

        return archived_count

    except Exception as e:
        logger.warning(f"Cleanup task failed (non-critical): {e}")
        return 0


# Create the DAG
with DAG(
    dag_id="model_training",
    default_args=default_args,
    description="Train bike demand forecasting models daily and register the best one",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml-training", "ml-pipeline"],
    max_active_runs=1,
) as dag:

    # Start task
    start = EmptyOperator(task_id="start")

    # Validate features are available
    task_validate = PythonOperator(
        task_id="validate_features",
        python_callable=validate_feature_availability,
        provide_context=True,
    )

    # Train models in parallel
    task_xgboost = PythonOperator(
        task_id="train_xgboost",
        python_callable=train_xgboost_model,
        provide_context=True,
    )

    task_lightgbm = PythonOperator(
        task_id="train_lightgbm",
        python_callable=train_lightgbm_model,
        provide_context=True,
    )

    task_catboost = PythonOperator(
        task_id="train_catboost",
        python_callable=train_catboost_model,
        provide_context=True,
    )

    # Compare and register best model
    task_compare = PythonOperator(
        task_id="compare_and_register",
        python_callable=compare_models_and_register_best,
        provide_context=True,
    )

    # Cleanup old models
    task_cleanup = PythonOperator(
        task_id="cleanup_old_models",
        python_callable=cleanup_old_models,
        provide_context=True,
    )

    # End task
    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> task_validate >> [task_xgboost, task_lightgbm, task_catboost] >> task_compare >> task_cleanup >> end
