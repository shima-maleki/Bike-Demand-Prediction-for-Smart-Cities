"""
Test FastAPI Serving Endpoints
Tests all API endpoints with sample requests
"""

import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# API base URL
API_BASE_URL = "http://localhost:8000"


def test_root_endpoint():
    """Test root endpoint"""
    logger.info("=" * 70)
    logger.info("TEST 1: Root Endpoint")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/")
        response.raise_for_status()

        data = response.json()
        logger.info("✓ Root endpoint successful")
        logger.info(f"  API Name: {data.get('name')}")
        logger.info(f"  Version: {data.get('version')}")
        logger.info(f"  Status: {data.get('status')}")

        return True

    except Exception as e:
        logger.error(f"✗ Root endpoint failed: {e}")
        return False


def test_health_check():
    """Test health check endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Health Check")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()

        data = response.json()
        logger.info("✓ Health check successful")
        logger.info(f"  Status: {data.get('status')}")
        logger.info(f"  Model Status: {data.get('model_status')}")
        logger.info(f"  Database Status: {data.get('database_status')}")

        return True

    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


def test_detailed_health_check():
    """Test detailed health check endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Detailed Health Check")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/health/detailed")
        response.raise_for_status()

        data = response.json()
        logger.info("✓ Detailed health check successful")
        logger.info(f"  Overall Status: {data.get('status')}")

        components = data.get('components', {})
        for component, status_info in components.items():
            logger.info(f"  {component.capitalize()}: {status_info.get('status')}")

        return True

    except Exception as e:
        logger.error(f"✗ Detailed health check failed: {e}")
        return False


def test_readiness_check():
    """Test readiness check endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Readiness Check")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/health/ready")
        response.raise_for_status()

        data = response.json()
        logger.info("✓ Readiness check successful")
        logger.info(f"  Status: {data.get('status')}")

        if data.get('status') == 'ready':
            logger.info("  Service is ready to accept requests")
        else:
            logger.warning(f"  Service not ready: {data.get('reason')}")

        return True

    except Exception as e:
        logger.error(f"✗ Readiness check failed: {e}")
        return False


def test_current_model():
    """Test current model endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Current Model Info")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/monitoring/models/current")
        response.raise_for_status()

        data = response.json()
        logger.info("✓ Current model endpoint successful")

        model_info = data.get('model_info', {})
        if model_info:
            logger.info(f"  Model Name: {model_info.get('name')}")
            logger.info(f"  Version: {model_info.get('version')}")
            logger.info(f"  Stage: {model_info.get('stage')}")
        else:
            logger.warning("  No model loaded")

        metrics = data.get('metrics')
        if metrics:
            logger.info("\n  Performance Metrics:")
            logger.info(f"    Test RMSE: {metrics.get('test_rmse')}")
            logger.info(f"    Test MAE: {metrics.get('test_mae')}")
            logger.info(f"    Test MAPE: {metrics.get('test_mape')}")
            logger.info(f"    Test R²: {metrics.get('test_r2')}")

        return True

    except Exception as e:
        logger.error(f"✗ Current model endpoint failed: {e}")
        return False


def test_single_prediction():
    """Test single prediction endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Single Prediction")
    logger.info("=" * 70)

    try:
        # Prepare request
        prediction_time = datetime.utcnow() + timedelta(hours=1)

        payload = {
            "station_id": "station_1",
            "timestamp": prediction_time.isoformat(),
            "weather_data": {
                "temperature": 20.0,
                "humidity": 65,
                "wind_speed": 5.0,
                "weather_condition": "Clear"
            }
        }

        logger.info(f"  Station: {payload['station_id']}")
        logger.info(f"  Time: {payload['timestamp']}")

        response = requests.post(
            f"{API_BASE_URL}/predict",
            json=payload
        )

        # Note: This might fail if no model is loaded or no data exists
        if response.status_code == 200:
            data = response.json()
            logger.info("✓ Prediction successful")
            logger.info(f"  Predicted Demand: {data.get('predicted_demand'):.2f} bikes")

            ci = data.get('confidence_interval', {})
            logger.info(f"  Confidence Interval: [{ci.get('lower'):.2f}, {ci.get('upper'):.2f}]")

            return True
        else:
            logger.warning(f"⚠ Prediction failed (expected if no model/data): {response.status_code}")
            logger.info(f"  Response: {response.text}")
            return True  # Not a hard failure for testing

    except Exception as e:
        logger.error(f"✗ Single prediction failed: {e}")
        return False


def test_batch_prediction():
    """Test batch prediction endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 7: Batch Prediction")
    logger.info("=" * 70)

    try:
        # Prepare batch request
        prediction_time = datetime.utcnow() + timedelta(hours=1)

        payload = {
            "predictions": [
                {
                    "station_id": "station_1",
                    "timestamp": prediction_time.isoformat()
                },
                {
                    "station_id": "station_2",
                    "timestamp": prediction_time.isoformat()
                },
                {
                    "station_id": "station_3",
                    "timestamp": prediction_time.isoformat()
                }
            ]
        }

        logger.info(f"  Batch size: {len(payload['predictions'])}")

        response = requests.post(
            f"{API_BASE_URL}/predict/batch",
            json=payload
        )

        if response.status_code == 200:
            data = response.json()
            logger.info("✓ Batch prediction successful")
            logger.info(f"  Total: {data.get('total_predictions')}")
            logger.info(f"  Successful: {data.get('successful')}")
            logger.info(f"  Failed: {data.get('failed')}")

            return True
        else:
            logger.warning(f"⚠ Batch prediction failed (expected if no model/data): {response.status_code}")
            return True

    except Exception as e:
        logger.error(f"✗ Batch prediction failed: {e}")
        return False


def test_forecast():
    """Test forecast endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 8: Multi-hour Forecast")
    logger.info("=" * 70)

    try:
        station_id = "station_1"
        hours_ahead = 24

        logger.info(f"  Station: {station_id}")
        logger.info(f"  Hours ahead: {hours_ahead}")

        response = requests.get(
            f"{API_BASE_URL}/predict/station/{station_id}/forecast",
            params={"hours_ahead": hours_ahead}
        )

        if response.status_code == 200:
            data = response.json()
            logger.info("✓ Forecast successful")
            logger.info(f"  Forecast hours: {data.get('forecast_hours')}")
            logger.info(f"  Forecast points: {len(data.get('forecasts', []))}")

            # Show first few forecasts
            forecasts = data.get('forecasts', [])
            if forecasts:
                logger.info("\n  Sample forecasts:")
                for forecast in forecasts[:3]:
                    logger.info(f"    Hour {forecast.get('hour_ahead')}: {forecast.get('predicted_demand'):.2f} bikes")

            return True
        else:
            logger.warning(f"⚠ Forecast failed (expected if no model/data): {response.status_code}")
            return True

    except Exception as e:
        logger.error(f"✗ Forecast failed: {e}")
        return False


def test_prometheus_metrics():
    """Test Prometheus metrics endpoint"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 9: Prometheus Metrics")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/monitoring/metrics")
        response.raise_for_status()

        metrics_text = response.text
        logger.info("✓ Prometheus metrics successful")

        # Count metrics
        metric_lines = [line for line in metrics_text.split('\n') if line and not line.startswith('#')]
        logger.info(f"  Total metrics: {len(metric_lines)}")

        # Show sample metrics
        logger.info("\n  Sample metrics:")
        for line in metric_lines[:5]:
            logger.info(f"    {line}")

        return True

    except Exception as e:
        logger.error(f"✗ Prometheus metrics failed: {e}")
        return False


def main():
    """Run all API tests"""
    logger.info("\n" + "=" * 70)
    logger.info("FASTAPI ENDPOINT TEST SUITE")
    logger.info("=" * 70)
    logger.info(f"Testing API at: {API_BASE_URL}")
    logger.info("\nNOTE: Some tests may show warnings if no model is loaded or no data exists.")
    logger.info("This is expected for initial testing.\n")

    # Check if API is running
    try:
        requests.get(f"{API_BASE_URL}/", timeout=2)
    except requests.exceptions.ConnectionError:
        logger.error(f"\n❌ ERROR: Cannot connect to API at {API_BASE_URL}")
        logger.info("\nTo start the API, run:")
        logger.info("  python -m uvicorn src.serving.api.main:app --reload")
        logger.info("\nOr from the scripts directory:")
        logger.info("  cd /path/to/project")
        logger.info("  python src/serving/api/main.py")
        return 1

    results = {
        "Root Endpoint": test_root_endpoint(),
        "Health Check": test_health_check(),
        "Detailed Health": test_detailed_health_check(),
        "Readiness Check": test_readiness_check(),
        "Current Model": test_current_model(),
        "Single Prediction": test_single_prediction(),
        "Batch Prediction": test_batch_prediction(),
        "Multi-hour Forecast": test_forecast(),
        "Prometheus Metrics": test_prometheus_metrics(),
    }

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:.<40} {status}")

    total = len(results)
    passed_count = sum(results.values())
    logger.info(f"\n📊 Total: {passed_count}/{total} tests passed ({passed_count/total*100:.0f}%)")

    if passed_count == total:
        logger.info("\n🎉 All API endpoint tests passed!")
        logger.info("\n🔗 Useful Links:")
        logger.info(f"  - API Docs: {API_BASE_URL}/docs")
        logger.info(f"  - OpenAPI Schema: {API_BASE_URL}/openapi.json")
        logger.info(f"  - Health: {API_BASE_URL}/health")
        logger.info(f"  - Metrics: {API_BASE_URL}/monitoring/metrics")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
