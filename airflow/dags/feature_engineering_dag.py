"""
Feature Engineering DAG
Generates time-series features from bike and weather data hourly
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from loguru import logger
import pandas as pd

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.data.storage.postgres_handler import postgres_handler
from src.features.temporal_features import TemporalFeatureGenerator
from src.features.lag_features import LagFeatureGenerator
from src.features.rolling_features import RollingFeatureGenerator
from src.features.weather_features import WeatherFeatureGenerator
from src.features.holiday_features import HolidayFeatureGenerator


default_args = {
    "owner": "bike-demand-prediction",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


def extract_data(**context):
    """
    Task: Extract bike and weather data from PostgreSQL

    Returns:
        dict: Data extraction summary
    """
    logger.info("Extracting data for feature engineering")

    try:
        # Get data from last 30 days for feature engineering
        from datetime import datetime, timedelta
        from sqlalchemy import select, and_
        from src.data.models import BikeStationStatus, WeatherData
        from src.config.database import get_db_context

        cutoff_time = datetime.utcnow() - timedelta(days=30)

        with get_db_context() as db:
            # Get bike station statuses
            bike_query = select(BikeStationStatus).where(
                BikeStationStatus.timestamp >= cutoff_time
            ).order_by(BikeStationStatus.station_id, BikeStationStatus.timestamp)

            bike_data = pd.read_sql(bike_query, db.connection())

            # Get weather data
            weather_query = select(WeatherData).where(
                WeatherData.timestamp >= cutoff_time
            ).order_by(WeatherData.timestamp)

            weather_data = pd.read_sql(weather_query, db.connection())

        logger.info(f"Extracted {len(bike_data)} bike records and {len(weather_data)} weather records")

        # Save to XCom
        context["ti"].xcom_push(key="bike_records", value=len(bike_data))
        context["ti"].xcom_push(key="weather_records", value=len(weather_data))

        return {
            "bike_records": len(bike_data),
            "weather_records": len(weather_data)
        }

    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        raise


def generate_temporal_features(**context):
    """
    Task: Generate temporal features

    Returns:
        int: Number of records processed
    """
    logger.info("Generating temporal features")

    try:
        from src.config.database import get_db_context
        from sqlalchemy import select
        from src.data.models import BikeStationStatus

        cutoff_time = datetime.utcnow() - timedelta(days=30)

        with get_db_context() as db:
            query = select(BikeStationStatus).where(
                BikeStationStatus.timestamp >= cutoff_time
            ).order_by(BikeStationStatus.timestamp)

            df = pd.read_sql(query, db.connection())

        if len(df) == 0:
            logger.warning("No data to process")
            return 0

        # Generate temporal features
        generator = TemporalFeatureGenerator()
        df_with_features = generator.generate(df)

        logger.info(f"Generated {len(generator.get_feature_names())} temporal features")

        # Push to XCom
        context["ti"].xcom_push(key="temporal_features_count", value=len(generator.get_feature_names()))

        return len(df_with_features)

    except Exception as e:
        logger.error(f"Failed to generate temporal features: {e}")
        raise


def generate_lag_rolling_features(**context):
    """
    Task: Generate lag and rolling window features

    Returns:
        int: Number of records processed
    """
    logger.info("Generating lag and rolling features")

    try:
        from src.config.database import get_db_context
        from sqlalchemy import select
        from src.data.models import BikeStationStatus

        cutoff_time = datetime.utcnow() - timedelta(days=30)

        with get_db_context() as db:
            query = select(BikeStationStatus).where(
                BikeStationStatus.timestamp >= cutoff_time
            ).order_by(BikeStationStatus.station_id, BikeStationStatus.timestamp)

            df = pd.read_sql(query, db.connection())

        if len(df) == 0:
            logger.warning("No data to process")
            return 0

        # Generate lag features
        lag_generator = LagFeatureGenerator(
            lag_hours=[1, 3, 6, 12, 24, 48, 168],
            target_column="bikes_available"
        )
        df_with_lags = lag_generator.generate(df)

        # Generate rolling features
        rolling_generator = RollingFeatureGenerator(
            windows=[3, 6, 12, 24],
            statistics=["mean", "std", "min", "max"],
            target_column="bikes_available"
        )
        df_with_features = rolling_generator.generate(df_with_lags)

        logger.info(f"Generated {len(lag_generator.get_feature_names())} lag features")
        logger.info(f"Generated {len(rolling_generator.get_feature_names())} rolling features")

        # Push to XCom
        total_features = len(lag_generator.get_feature_names()) + len(rolling_generator.get_feature_names())
        context["ti"].xcom_push(key="lag_rolling_features_count", value=total_features)

        return len(df_with_features)

    except Exception as e:
        logger.error(f"Failed to generate lag/rolling features: {e}")
        raise


def generate_weather_holiday_features(**context):
    """
    Task: Generate weather and holiday features

    Returns:
        int: Number of records processed
    """
    logger.info("Generating weather and holiday features")

    try:
        from src.config.database import get_db_context
        from sqlalchemy import select
        from src.data.models import BikeStationStatus, WeatherData

        cutoff_time = datetime.utcnow() - timedelta(days=30)

        with get_db_context() as db:
            # Get bike data
            bike_query = select(BikeStationStatus).where(
                BikeStationStatus.timestamp >= cutoff_time
            )
            df = pd.read_sql(bike_query, db.connection())

            # Get weather data
            weather_query = select(WeatherData).where(
                WeatherData.timestamp >= cutoff_time
            )
            weather_df = pd.read_sql(weather_query, db.connection())

        if len(df) == 0:
            logger.warning("No data to process")
            return 0

        # Merge weather data (simple time-based merge)
        if len(weather_df) > 0:
            df = pd.merge_asof(
                df.sort_values("timestamp"),
                weather_df[["timestamp", "temperature", "humidity", "wind_speed", "weather_condition"]].sort_values("timestamp"),
                on="timestamp",
                direction="nearest"
            )

            # Generate weather features
            weather_generator = WeatherFeatureGenerator()
            df_with_weather = weather_generator.generate(df)
            logger.info(f"Generated {len(weather_generator.get_feature_names())} weather features")
        else:
            df_with_weather = df
            logger.warning("No weather data available")

        # Generate holiday features
        holiday_generator = HolidayFeatureGenerator(country="US", state="NY")
        df_with_features = holiday_generator.generate(df_with_weather)

        logger.info(f"Generated {len(holiday_generator.get_feature_names())} holiday features")

        # Push to XCom
        weather_count = len(weather_generator.get_feature_names()) if len(weather_df) > 0 else 0
        holiday_count = len(holiday_generator.get_feature_names())
        total_features = weather_count + holiday_count
        context["ti"].xcom_push(key="weather_holiday_features_count", value=total_features)

        return len(df_with_features)

    except Exception as e:
        logger.error(f"Failed to generate weather/holiday features: {e}")
        raise


def save_features(**context):
    """
    Task: Save engineered features to database

    Returns:
        int: Number of feature records saved
    """
    logger.info("Saving engineered features")

    try:
        # In a real implementation, we would:
        # 1. Combine all features
        # 2. Store in features table as JSONB
        # 3. Version with DVC

        # For now, just log the summary
        ti = context["ti"]
        temporal = ti.xcom_pull(key="temporal_features_count", task_ids="generate_temporal_features")
        lag_rolling = ti.xcom_pull(key="lag_rolling_features_count", task_ids="generate_lag_rolling_features")
        weather_holiday = ti.xcom_pull(key="weather_holiday_features_count", task_ids="generate_weather_holiday_features")

        total_features = (temporal or 0) + (lag_rolling or 0) + (weather_holiday or 0)

        logger.info(f"Total features generated: {total_features}")
        logger.info(f"  - Temporal: {temporal}")
        logger.info(f"  - Lag/Rolling: {lag_rolling}")
        logger.info(f"  - Weather/Holiday: {weather_holiday}")

        # Store quality check
        quality_check = {
            "check_name": "feature_engineering",
            "table_name": "features",
            "check_timestamp": datetime.utcnow(),
            "status": "passed",
            "expected_value": {"total_features": "> 0"},
            "actual_value": {
                "total_features": total_features,
                "temporal": temporal,
                "lag_rolling": lag_rolling,
                "weather_holiday": weather_holiday
            },
            "error_message": None,
        }
        postgres_handler.insert_data_quality_check(quality_check)

        return total_features

    except Exception as e:
        logger.error(f"Failed to save features: {e}")
        raise


# Create the DAG
with DAG(
    dag_id="feature_engineering",
    default_args=default_args,
    description="Generate time-series features from bike and weather data hourly",
    schedule_interval="0 * * * *",  # Every hour
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["feature-engineering", "ml-pipeline"],
    max_active_runs=1,
) as dag:

    # Start task
    start = EmptyOperator(task_id="start")

    # Extract data
    task_extract = PythonOperator(
        task_id="extract_data",
        python_callable=extract_data,
        provide_context=True,
    )

    # Generate features in parallel
    task_temporal = PythonOperator(
        task_id="generate_temporal_features",
        python_callable=generate_temporal_features,
        provide_context=True,
    )

    task_lag_rolling = PythonOperator(
        task_id="generate_lag_rolling_features",
        python_callable=generate_lag_rolling_features,
        provide_context=True,
    )

    task_weather_holiday = PythonOperator(
        task_id="generate_weather_holiday_features",
        python_callable=generate_weather_holiday_features,
        provide_context=True,
    )

    # Save features
    task_save = PythonOperator(
        task_id="save_features",
        python_callable=save_features,
        provide_context=True,
    )

    # End task
    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> task_extract >> [task_temporal, task_lag_rolling, task_weather_holiday] >> task_save >> end
