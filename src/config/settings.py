"""
Application Settings and Configuration
Using Pydantic Settings for environment variable management
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    user: str = Field(default="postgres", description="PostgreSQL user")
    password: str = Field(default="postgres", description="PostgreSQL password")
    database: str = Field(default="bike_demand_db", description="Database name")

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_connection_string(self) -> str:
        """Generate async PostgreSQL connection string"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    model_config = SettingsConfigDict(env_prefix="DB_", case_sensitive=False)


class CitiBikeAPISettings(BaseSettings):
    """Citi Bike API configuration"""

    base_url: str = Field(
        default="https://gbfs.citibikenyc.com/gbfs/en",
        description="Citi Bike GBFS base URL",
    )
    station_information_url: str = Field(
        default="https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
    )
    station_status_url: str = Field(
        default="https://gbfs.citibikenyc.com/gbfs/en/station_status.json"
    )
    timeout: int = Field(default=30, description="API timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="CITIBIKE_", case_sensitive=False)


class WeatherAPISettings(BaseSettings):
    """OpenWeatherMap API configuration"""

    api_key: str = Field(default="", description="OpenWeatherMap API key")
    base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5", description="API base URL"
    )
    units: str = Field(default="metric", description="Temperature units (metric/imperial)")
    timeout: int = Field(default=30, description="API timeout in seconds")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        import os
        # Only require API key in production environment
        environment = os.getenv("ENVIRONMENT", "development")
        if not v and environment == "production":
            raise ValueError("OpenWeatherMap API key is required in production")
        return v

    model_config = SettingsConfigDict(env_prefix="WEATHER_", case_sensitive=False)


class MLflowSettings(BaseSettings):
    """MLflow configuration"""

    tracking_uri: str = Field(
        default="http://localhost:5000", description="MLflow tracking server URI"
    )
    experiment_name: str = Field(
        default="bike_demand_forecasting", description="MLflow experiment name"
    )
    artifact_location: Optional[str] = Field(
        default=None, description="Artifact storage location"
    )
    model_registry_uri: Optional[str] = Field(
        default=None, description="Model registry URI"
    )

    model_config = SettingsConfigDict(env_prefix="MLFLOW_", case_sensitive=False)


class AirflowSettings(BaseSettings):
    """Airflow configuration"""

    home: str = Field(default="./airflow", description="Airflow home directory")
    dags_folder: str = Field(default="./airflow/dags", description="DAGs folder")
    executor: str = Field(default="LocalExecutor", description="Airflow executor")
    load_examples: bool = Field(default=False, description="Load example DAGs")

    model_config = SettingsConfigDict(env_prefix="AIRFLOW_", case_sensitive=False)


class ModelSettings(BaseSettings):
    """Model training configuration"""

    random_seed: int = Field(default=42, description="Random seed for reproducibility")
    train_split: float = Field(default=0.7, description="Training data split ratio")
    val_split: float = Field(default=0.15, description="Validation data split ratio")
    test_split: float = Field(default=0.15, description="Test data split ratio")
    forecast_horizon_hours: int = Field(
        default=24, description="Forecast horizon in hours"
    )
    retraining_interval_days: int = Field(
        default=7, description="Model retraining interval in days"
    )

    model_config = SettingsConfigDict(env_prefix="MODEL_", case_sensitive=False)


class FeatureSettings(BaseSettings):
    """Feature engineering configuration"""

    lag_hours: list[int] = Field(
        default=[1, 3, 6, 12, 24, 48, 168], description="Lag feature hours"
    )
    rolling_windows: list[int] = Field(
        default=[3, 6, 12, 24], description="Rolling window sizes in hours"
    )
    feature_version: str = Field(default="v1.0", description="Feature version")

    model_config = SettingsConfigDict(env_prefix="FEATURE_", case_sensitive=False)


class APISettings(BaseSettings):
    """FastAPI application configuration"""

    title: str = Field(
        default="Bike Demand Prediction API", description="API title"
    )
    description: str = Field(
        default="Level 2 MLOps bike demand forecasting system",
        description="API description",
    )
    version: str = Field(default="0.1.0", description="API version")
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    log_level: str = Field(default="info", description="Logging level")

    model_config = SettingsConfigDict(env_prefix="API_", case_sensitive=False)


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration"""

    enable_prometheus: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    enable_data_drift_detection: bool = Field(
        default=True, description="Enable data drift detection"
    )
    drift_detection_threshold: float = Field(
        default=0.3, description="Data drift threshold"
    )
    performance_degradation_threshold: float = Field(
        default=0.1, description="Performance degradation threshold (10%)"
    )

    model_config = SettingsConfigDict(env_prefix="MONITORING_", case_sensitive=False)


class DVCSettings(BaseSettings):
    """DVC configuration"""

    remote_name: str = Field(default="origin", description="DVC remote name")
    remote_url: Optional[str] = Field(default=None, description="DVC remote storage URL")

    model_config = SettingsConfigDict(env_prefix="DVC_", case_sensitive=False)


class Settings(BaseSettings):
    """Main application settings"""

    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Project info
    project_name: str = Field(
        default="bike-demand-prediction", description="Project name"
    )
    project_version: str = Field(default="0.1.0", description="Project version")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    citibike_api: CitiBikeAPISettings = Field(default_factory=CitiBikeAPISettings)
    weather_api: WeatherAPISettings = Field(default_factory=WeatherAPISettings)
    mlflow: MLflowSettings = Field(default_factory=MLflowSettings)
    airflow: AirflowSettings = Field(default_factory=AirflowSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    feature: FeatureSettings = Field(default_factory=FeatureSettings)
    api: APISettings = Field(default_factory=APISettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    dvc: DVCSettings = Field(default_factory=DVCSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="allow"
    )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for quick access
settings = get_settings()
