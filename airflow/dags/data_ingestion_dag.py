"""
Citi Bike Data Ingestion DAG
Collects station information and real-time status every 15 minutes
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from loguru import logger

# Add src to Python path for imports
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.data.collectors.citi_bike_collector import CitiBikeCollector
from src.data.storage.postgres_handler import postgres_handler


# Default arguments for the DAG
default_args = {
    "owner": "bike-demand-prediction",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=10),
}


def collect_station_information(**context):
    """
    Task: Collect and store bike station information

    Returns:
        int: Number of stations collected
    """
    logger.info("Starting station information collection")

    try:
        with CitiBikeCollector() as collector:
            # Collect station information
            data = collector.collect_station_information()

            # Parse the data
            stations = collector.parse_station_information(data)

            # Store in database
            count = postgres_handler.upsert_stations(stations)

            logger.info(f"Successfully collected and stored {count} stations")

            # Push to XCom for downstream tasks
            context["ti"].xcom_push(key="stations_count", value=count)

            return count

    except Exception as e:
        logger.error(f"Failed to collect station information: {e}")
        raise


def collect_station_status(**context):
    """
    Task: Collect and store real-time station status

    Returns:
        int: Number of status records collected
    """
    logger.info("Starting station status collection")

    try:
        with CitiBikeCollector() as collector:
            # Collect station status
            data = collector.collect_station_status()

            # Parse the data
            statuses = collector.parse_station_status(data)

            # Store in database
            count = postgres_handler.insert_station_statuses(statuses)

            logger.info(f"Successfully collected and stored {count} station statuses")

            # Push to XCom for downstream tasks
            context["ti"].xcom_push(key="statuses_count", value=count)

            return count

    except Exception as e:
        logger.error(f"Failed to collect station status: {e}")
        raise


def validate_data_quality(**context):
    """
    Task: Validate data quality of collected data

    Returns:
        dict: Validation results
    """
    logger.info("Starting data quality validation")

    try:
        # Pull from XCom
        ti = context["ti"]
        stations_count = ti.xcom_pull(key="stations_count", task_ids="collect_station_information")
        statuses_count = ti.xcom_pull(key="statuses_count", task_ids="collect_station_status")

        # Basic validation
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "stations_collected": stations_count,
            "statuses_collected": statuses_count,
            "validation_passed": True,
            "checks": []
        }

        # Check 1: Stations collected
        if stations_count == 0:
            validation_results["validation_passed"] = False
            validation_results["checks"].append({
                "check": "stations_count",
                "status": "failed",
                "message": "No stations collected"
            })
        else:
            validation_results["checks"].append({
                "check": "stations_count",
                "status": "passed",
                "value": stations_count
            })

        # Check 2: Statuses collected
        if statuses_count == 0:
            validation_results["validation_passed"] = False
            validation_results["checks"].append({
                "check": "statuses_count",
                "status": "failed",
                "message": "No statuses collected"
            })
        else:
            validation_results["checks"].append({
                "check": "statuses_count",
                "status": "passed",
                "value": statuses_count
            })

        # Check 3: Counts should match
        if stations_count != statuses_count:
            validation_results["checks"].append({
                "check": "count_match",
                "status": "warning",
                "message": f"Mismatch: {stations_count} stations vs {statuses_count} statuses"
            })
        else:
            validation_results["checks"].append({
                "check": "count_match",
                "status": "passed"
            })

        # Store validation result in database
        quality_check = {
            "check_name": "citi_bike_data_ingestion",
            "table_name": "bike_station_status",
            "check_timestamp": datetime.utcnow(),
            "status": "passed" if validation_results["validation_passed"] else "failed",
            "expected_value": {"stations": "> 0", "statuses": "> 0"},
            "actual_value": {
                "stations": stations_count,
                "statuses": statuses_count
            },
            "error_message": None if validation_results["validation_passed"] else "Data validation failed",
        }
        postgres_handler.insert_data_quality_check(quality_check)

        logger.info(f"Data quality validation completed: {validation_results}")

        if not validation_results["validation_passed"]:
            raise ValueError("Data quality validation failed")

        return validation_results

    except Exception as e:
        logger.error(f"Data quality validation error: {e}")
        raise


def log_collection_metrics(**context):
    """
    Task: Log collection metrics for monitoring

    Returns:
        dict: Collection metrics
    """
    logger.info("Logging collection metrics")

    try:
        ti = context["ti"]
        stations_count = ti.xcom_pull(key="stations_count", task_ids="collect_station_information")
        statuses_count = ti.xcom_pull(key="statuses_count", task_ids="collect_station_status")

        metrics = {
            "dag_run_id": context["dag_run"].run_id,
            "execution_date": context["execution_date"].isoformat(),
            "stations_collected": stations_count,
            "statuses_collected": statuses_count,
            "collection_timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Collection metrics: {metrics}")

        return metrics

    except Exception as e:
        logger.error(f"Failed to log metrics: {e}")
        raise


# Create the DAG
with DAG(
    dag_id="citi_bike_data_ingestion",
    default_args=default_args,
    description="Collect Citi Bike station information and real-time status every 15 minutes",
    schedule_interval="*/15 * * * *",  # Every 15 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["citi-bike", "data-ingestion", "real-time"],
    max_active_runs=1,
) as dag:

    # Start task
    start = EmptyOperator(task_id="start")

    # Collect station information
    task_collect_station_info = PythonOperator(
        task_id="collect_station_information",
        python_callable=collect_station_information,
        provide_context=True,
    )

    # Collect station status
    task_collect_station_status = PythonOperator(
        task_id="collect_station_status",
        python_callable=collect_station_status,
        provide_context=True,
    )

    # Validate data quality
    task_validate_quality = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_data_quality,
        provide_context=True,
    )

    # Log metrics
    task_log_metrics = PythonOperator(
        task_id="log_collection_metrics",
        python_callable=log_collection_metrics,
        provide_context=True,
    )

    # End task
    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> [task_collect_station_info, task_collect_station_status]
    [task_collect_station_info, task_collect_station_status] >> task_validate_quality
    task_validate_quality >> task_log_metrics >> end
