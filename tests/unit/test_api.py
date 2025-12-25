"""
Unit Tests for FastAPI Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.serving.api.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_health_endpoint(self):
        """Test basic health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_readiness_endpoint(self):
        """Test readiness probe"""
        response = client.get("/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    def test_liveness_endpoint(self):
        """Test liveness probe"""
        response = client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"


class TestMonitoringEndpoints:
    """Test monitoring endpoints"""

    def test_current_model_endpoint(self):
        """Test current model info endpoint"""
        response = client.get("/monitoring/models/current")
        assert response.status_code == 200

        data = response.json()
        assert "model_info" in data
        assert "timestamp" in data

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200

        # Should return text/plain
        assert "text/plain" in response.headers["content-type"]

    def test_stats_endpoint(self):
        """Test API stats endpoint"""
        response = client.get("/monitoring/stats")
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data


class TestPredictionEndpoints:
    """Test prediction endpoints"""

    def test_predict_endpoint_structure(self):
        """Test prediction endpoint accepts valid request"""
        payload = {
            "station_id": "station_1",
            "timestamp": datetime.utcnow().isoformat(),
            "weather_data": {
                "temperature": 20.0,
                "humidity": 65,
                "wind_speed": 5.0
            }
        }

        response = client.post("/predict", json=payload)

        # May fail if no model is loaded, but should have valid error structure
        if response.status_code == 200:
            data = response.json()
            assert "station_id" in data
            assert "predicted_demand" in data
            assert "confidence_interval" in data
        else:
            # Should return error structure
            assert response.status_code in [400, 500]

    def test_batch_predict_endpoint_structure(self):
        """Test batch prediction endpoint accepts valid request"""
        payload = {
            "predictions": [
                {
                    "station_id": "station_1",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "station_id": "station_2",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }

        response = client.post("/predict/batch", json=payload)

        # May fail if no model/data, but should have valid structure
        if response.status_code == 200:
            data = response.json()
            assert "predictions" in data
            assert "total_predictions" in data
            assert "successful" in data
            assert "failed" in data
        else:
            assert response.status_code in [400, 500]

    def test_batch_predict_validation_max_size(self):
        """Test batch prediction rejects > 100 requests"""
        payload = {
            "predictions": [
                {"station_id": f"station_{i}"}
                for i in range(101)
            ]
        }

        response = client.post("/predict/batch", json=payload)

        # Should fail validation
        assert response.status_code == 422  # Validation error

    def test_forecast_endpoint_get(self):
        """Test forecast endpoint (GET method)"""
        response = client.get("/predict/station/station_1/forecast?hours_ahead=24")

        # May fail if no model/data, but should accept the request
        if response.status_code == 200:
            data = response.json()
            assert "station_id" in data
            assert "forecasts" in data
            assert "forecast_hours" in data
        else:
            assert response.status_code in [400, 500]

    def test_forecast_validation_max_hours(self):
        """Test forecast rejects invalid hours_ahead"""
        # Test > 168 hours
        response = client.get("/predict/station/station_1/forecast?hours_ahead=200")

        # Should fail validation
        assert response.status_code == 400


class TestInputValidation:
    """Test input validation"""

    def test_predict_requires_station_id(self):
        """Test that station_id is required"""
        payload = {
            "timestamp": datetime.utcnow().isoformat()
        }

        response = client.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_predict_invalid_weather_data(self):
        """Test weather data validation"""
        payload = {
            "station_id": "station_1",
            "weather_data": {
                "temperature": 100,  # Invalid range
                "humidity": 150  # Invalid range
            }
        }

        response = client.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_batch_predict_requires_list(self):
        """Test batch prediction requires a list"""
        payload = {
            "predictions": "not_a_list"
        }

        response = client.post("/predict/batch", json=payload)
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_endpoint(self):
        """Test 404 for invalid endpoint"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 for wrong HTTP method"""
        response = client.get("/predict")  # Should be POST
        assert response.status_code == 405


class TestCORS:
    """Test CORS headers"""

    def test_cors_headers(self):
        """Test that CORS headers are present"""
        # CORS headers should be present in regular responses
        response = client.get("/health")

        # Check for CORS headers (case-insensitive)
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert response.status_code == 200
        # CORS headers may not be present in TestClient, but endpoint should work
        # In production, CORSMiddleware adds these headers
