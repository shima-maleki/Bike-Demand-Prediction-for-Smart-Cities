"""
Weather Enrichment DAG
Collects weather data for NYC every 30 minutes
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from loguru import logger

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.data.collectors.weather_collector import WeatherCollector
from src.data.storage.postgres_handler import postgres_handler


default_args = {
    "owner": "bike-demand-prediction",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=10),
}


def collect_weather_data(**context):
    """
    Task: Collect weather data for NYC

    Returns:
        int: Number of weather records collected
    """
    logger.info("Starting weather data collection")

    try:
        with WeatherCollector() as collector:
            # Get NYC center coordinates
            lat, lon = collector.get_nyc_center_coordinates()

            # Collect weather data
            logger.info(f"Collecting weather for NYC ({lat}, {lon})")
            data = collector.collect(lat=lat, lon=lon)

            # Parse the data
            weather_record = collector.parse_weather_data(
                data["weather_data"], location_id="NYC_Center"
            )

            # Store in database
            count = postgres_handler.insert_weather_data([weather_record])

            logger.info(f"Successfully collected and stored {count} weather record")

            # Push to XCom
            context["ti"].xcom_push(key="weather_count", value=count)
            context["ti"].xcom_push(key="temperature", value=weather_record["temperature"])
            context["ti"].xcom_push(key="weather_condition", value=weather_record["weather_condition"])

            return count

    except Exception as e:
        logger.error(f"Failed to collect weather data: {e}")
        raise


def validate_weather_quality(**context):
    """
    Task: Validate weather data quality

    Returns:
        dict: Validation results
    """
    logger.info("Starting weather data quality validation")

    try:
        ti = context["ti"]
        weather_count = ti.xcom_pull(key="weather_count", task_ids="collect_weather_data")
        temperature = ti.xcom_pull(key="temperature", task_ids="collect_weather_data")
        condition = ti.xcom_pull(key="weather_condition", task_ids="collect_weather_data")

        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "weather_records_collected": weather_count,
            "validation_passed": True,
            "checks": []
        }

        # Check 1: Weather collected
        if weather_count == 0:
            validation_results["validation_passed"] = False
            validation_results["checks"].append({
                "check": "weather_collected",
                "status": "failed",
                "message": "No weather data collected"
            })
        else:
            validation_results["checks"].append({
                "check": "weather_collected",
                "status": "passed"
            })

        # Check 2: Temperature is reasonable for NYC (-20 to 45 Celsius)
        if temperature is not None:
            if temperature < -20 or temperature > 45:
                validation_results["checks"].append({
                    "check": "temperature_range",
                    "status": "warning",
                    "message": f"Unusual temperature: {temperature}°C"
                })
            else:
                validation_results["checks"].append({
                    "check": "temperature_range",
                    "status": "passed",
                    "value": temperature
                })

        # Check 3: Weather condition is not None
        if not condition:
            validation_results["checks"].append({
                "check": "weather_condition",
                "status": "failed",
                "message": "Missing weather condition"
            })
            validation_results["validation_passed"] = False
        else:
            validation_results["checks"].append({
                "check": "weather_condition",
                "status": "passed",
                "value": condition
            })

        # Store validation result
        quality_check = {
            "check_name": "weather_data_collection",
            "table_name": "weather_data",
            "check_timestamp": datetime.utcnow(),
            "status": "passed" if validation_results["validation_passed"] else "failed",
            "expected_value": {"records": "> 0", "temp_range": "-20 to 45"},
            "actual_value": {
                "records": weather_count,
                "temperature": temperature,
                "condition": condition
            },
            "error_message": None if validation_results["validation_passed"] else "Weather validation failed",
        }
        postgres_handler.insert_data_quality_check(quality_check)

        logger.info(f"Weather quality validation: {validation_results}")

        if not validation_results["validation_passed"]:
            raise ValueError("Weather quality validation failed")

        return validation_results

    except Exception as e:
        logger.error(f"Weather quality validation error: {e}")
        raise


def log_weather_metrics(**context):
    """
    Task: Log weather collection metrics

    Returns:
        dict: Weather metrics
    """
    logger.info("Logging weather metrics")

    try:
        ti = context["ti"]
        weather_count = ti.xcom_pull(key="weather_count", task_ids="collect_weather_data")
        temperature = ti.xcom_pull(key="temperature", task_ids="collect_weather_data")
        condition = ti.xcom_pull(key="weather_condition", task_ids="collect_weather_data")

        metrics = {
            "dag_run_id": context["dag_run"].run_id,
            "execution_date": context["execution_date"].isoformat(),
            "weather_records": weather_count,
            "temperature": temperature,
            "weather_condition": condition,
            "collection_timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Weather metrics: {metrics}")

        return metrics

    except Exception as e:
        logger.error(f"Failed to log weather metrics: {e}")
        raise


# Create the DAG
with DAG(
    dag_id="weather_enrichment",
    default_args=default_args,
    description="Collect weather data for NYC every 30 minutes",
    schedule_interval="*/30 * * * *",  # Every 30 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["weather", "data-enrichment", "real-time"],
    max_active_runs=1,
) as dag:

    # Start task
    start = EmptyOperator(task_id="start")

    # Collect weather data
    task_collect_weather = PythonOperator(
        task_id="collect_weather_data",
        python_callable=collect_weather_data,
        provide_context=True,
    )

    # Validate data quality
    task_validate_quality = PythonOperator(
        task_id="validate_weather_quality",
        python_callable=validate_weather_quality,
        provide_context=True,
    )

    # Log metrics
    task_log_metrics = PythonOperator(
        task_id="log_weather_metrics",
        python_callable=log_weather_metrics,
        provide_context=True,
    )

    # End task
    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> task_collect_weather >> task_validate_quality >> task_log_metrics >> end
