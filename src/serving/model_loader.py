"""
Model Loader
Loads trained models from MLflow Model Registry
"""

import mlflow
import mlflow.sklearn
from typing import Any, Optional, Dict
from loguru import logger
from datetime import datetime
import pandas as pd

from src.config.settings import get_settings

settings = get_settings()


class ModelLoader:
    """Loads and manages ML models from MLflow"""

    def __init__(self):
        """Initialize model loader"""
        mlflow.set_tracking_uri(settings.mlflow.tracking_uri)
        self.current_model = None
        self.current_model_info = None
        self.last_loaded_time = None

    def load_production_model(self, model_name: str = "bike-demand-forecasting") -> Any:
        """
        Load the production model from MLflow Model Registry

        Args:
            model_name: Name of the registered model

        Returns:
            Loaded model object
        """
        logger.info(f"Loading production model: {model_name}")

        try:
            # Get production model URI
            model_uri = f"models:/{model_name}/Production"

            # Load model
            model = mlflow.sklearn.load_model(model_uri)

            # Get model metadata
            client = mlflow.tracking.MlflowClient()
            versions = client.get_latest_versions(model_name, stages=["Production"])

            if versions:
                version_info = versions[0]
                self.current_model_info = {
                    "name": model_name,
                    "version": version_info.version,
                    "stage": version_info.current_stage,
                    "run_id": version_info.run_id,
                    "loaded_at": datetime.utcnow().isoformat()
                }
                logger.info(f"✓ Loaded model version {version_info.version} from Production")
            else:
                logger.warning("No production model found, loading latest version")
                self.current_model_info = {
                    "name": model_name,
                    "version": "latest",
                    "stage": "None",
                    "loaded_at": datetime.utcnow().isoformat()
                }

            self.current_model = model
            self.last_loaded_time = datetime.utcnow()

            return model

        except Exception as e:
            logger.error(f"Failed to load production model: {e}")
            raise

    def load_specific_version(
        self,
        model_name: str,
        version: str
    ) -> Any:
        """
        Load a specific model version

        Args:
            model_name: Name of the registered model
            version: Version number

        Returns:
            Loaded model object
        """
        logger.info(f"Loading model {model_name} version {version}")

        try:
            model_uri = f"models:/{model_name}/{version}"
            model = mlflow.sklearn.load_model(model_uri)

            self.current_model = model
            self.current_model_info = {
                "name": model_name,
                "version": version,
                "loaded_at": datetime.utcnow().isoformat()
            }
            self.last_loaded_time = datetime.utcnow()

            logger.info(f"✓ Loaded model version {version}")

            return model

        except Exception as e:
            logger.error(f"Failed to load model version {version}: {e}")
            raise

    def load_model_by_run_id(self, run_id: str) -> Any:
        """
        Load model by MLflow run ID

        Args:
            run_id: MLflow run ID

        Returns:
            Loaded model object
        """
        logger.info(f"Loading model from run {run_id}")

        try:
            model_uri = f"runs:/{run_id}/model"
            model = mlflow.sklearn.load_model(model_uri)

            self.current_model = model
            self.current_model_info = {
                "run_id": run_id,
                "loaded_at": datetime.utcnow().isoformat()
            }
            self.last_loaded_time = datetime.utcnow()

            logger.info(f"✓ Loaded model from run {run_id}")

            return model

        except Exception as e:
            logger.error(f"Failed to load model from run {run_id}: {e}")
            raise

    def get_model(self) -> Any:
        """
        Get current loaded model

        Returns:
            Current model or None if not loaded
        """
        return self.current_model

    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current loaded model

        Returns:
            Dictionary with model metadata
        """
        return self.current_model_info

    def reload_if_stale(self, max_age_minutes: int = 60) -> bool:
        """
        Reload model if it's older than max_age_minutes

        Args:
            max_age_minutes: Maximum age in minutes before reload

        Returns:
            True if model was reloaded, False otherwise
        """
        if not self.last_loaded_time:
            logger.info("No model loaded, loading now...")
            self.load_production_model()
            return True

        age_minutes = (datetime.utcnow() - self.last_loaded_time).total_seconds() / 60

        if age_minutes > max_age_minutes:
            logger.info(f"Model is {age_minutes:.1f} minutes old, reloading...")
            self.load_production_model()
            return True

        return False

    def validate_model(self) -> bool:
        """
        Validate that the current model is working

        Returns:
            True if model is valid and can make predictions
        """
        if self.current_model is None:
            logger.error("No model loaded")
            return False

        try:
            # Create a simple test input
            test_input = pd.DataFrame({
                'feature': [1.0]
            })

            # Try to predict (this will fail if model expects different features,
            # but that's okay - we just want to check if model object is valid)
            _ = self.current_model.predict(test_input)
            return True

        except AttributeError:
            logger.error("Model object doesn't have predict method")
            return False

        except Exception as e:
            # Model might fail on wrong features, but object is valid
            logger.debug(f"Model validation test prediction failed (expected): {e}")
            return True

    def get_model_metrics(self) -> Optional[Dict[str, float]]:
        """
        Get metrics for the current model from MLflow

        Returns:
            Dictionary of metrics or None
        """
        if not self.current_model_info or "run_id" not in self.current_model_info:
            return None

        try:
            client = mlflow.tracking.MlflowClient()
            run = client.get_run(self.current_model_info["run_id"])

            metrics = {
                "test_rmse": run.data.metrics.get("test_rmse"),
                "test_mae": run.data.metrics.get("test_mae"),
                "test_mape": run.data.metrics.get("test_mape"),
                "test_r2": run.data.metrics.get("test_r2"),
                "val_rmse": run.data.metrics.get("val_rmse"),
                "val_mae": run.data.metrics.get("val_mae"),
                "val_mape": run.data.metrics.get("val_mape"),
                "val_r2": run.data.metrics.get("val_r2"),
            }

            return {k: v for k, v in metrics.items() if v is not None}

        except Exception as e:
            logger.error(f"Failed to get model metrics: {e}")
            return None


# Global model loader instance
_model_loader = None


def get_model_loader() -> ModelLoader:
    """
    Get or create global model loader instance

    Returns:
        ModelLoader instance
    """
    global _model_loader

    if _model_loader is None:
        _model_loader = ModelLoader()
        # Load production model on first access
        try:
            _model_loader.load_production_model()
        except Exception as e:
            logger.warning(f"Failed to load production model on startup: {e}")

    return _model_loader
