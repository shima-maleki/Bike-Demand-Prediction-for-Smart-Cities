"""
Unit Tests for Data Collectors
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.data.collectors.citi_bike_collector import CitiBikeCollector


class TestCitiBikeCollector:
    """Test cases for Citi Bike collector"""

    @pytest.fixture
    def mock_station_info_response(self):
        """Mock station information API response"""
        return {
            "data": {
                "stations": [
                    {
                        "station_id": "test-station-1",
                        "name": "Test Station 1",
                        "lat": 40.7614,
                        "lon": -73.9776,
                        "capacity": 50,
                    },
                    {
                        "station_id": "test-station-2",
                        "name": "Test Station 2",
                        "lat": 40.7580,
                        "lon": -73.9855,
                        "capacity": 35,
                    },
                ]
            },
            "last_updated": 1640000000,
            "ttl": 10,
        }

    @pytest.fixture
    def mock_station_status_response(self):
        """Mock station status API response"""
        return {
            "data": {
                "stations": [
                    {
                        "station_id": "test-station-1",
                        "num_bikes_available": 12,
                        "num_bikes_disabled": 2,
                        "num_docks_available": 36,
                        "num_docks_disabled": 0,
                        "is_installed": 1,
                        "is_renting": 1,
                        "is_returning": 1,
                    },
                    {
                        "station_id": "test-station-2",
                        "num_bikes_available": 8,
                        "num_bikes_disabled": 1,
                        "num_docks_available": 26,
                        "num_docks_disabled": 0,
                        "is_installed": 1,
                        "is_renting": 1,
                        "is_returning": 1,
                    },
                ]
            },
            "last_updated": 1640000000,
            "ttl": 10,
        }

    def test_collector_initialization(self):
        """Test collector initialization"""
        collector = CitiBikeCollector()
        assert collector.base_url is not None
        assert collector.timeout > 0
        assert collector.station_info_url is not None
        assert collector.station_status_url is not None

    def test_validate_station_information_success(
        self, mock_station_info_response
    ):
        """Test validation of valid station information"""
        collector = CitiBikeCollector()
        result = collector.validate_station_information(mock_station_info_response)
        assert result is True

    def test_validate_station_information_missing_data(self):
        """Test validation fails with missing data key"""
        collector = CitiBikeCollector()
        invalid_data = {"last_updated": 1640000000}
        result = collector.validate_station_information(invalid_data)
        assert result is False

    def test_validate_station_information_empty_stations(self):
        """Test validation fails with empty stations list"""
        collector = CitiBikeCollector()
        invalid_data = {"data": {"stations": []}}
        result = collector.validate_station_information(invalid_data)
        assert result is False

    def test_validate_station_status_success(self, mock_station_status_response):
        """Test validation of valid station status"""
        collector = CitiBikeCollector()
        result = collector.validate_station_status(mock_station_status_response)
        assert result is True

    def test_parse_station_information(self, mock_station_info_response):
        """Test parsing station information"""
        collector = CitiBikeCollector()
        stations = collector.parse_station_information(mock_station_info_response)

        assert len(stations) == 2
        assert stations[0]["station_id"] == "test-station-1"
        assert stations[0]["name"] == "Test Station 1"
        assert stations[0]["latitude"] == 40.7614
        assert stations[0]["longitude"] == -73.9776
        assert stations[0]["capacity"] == 50
        assert stations[0]["is_active"] is True

    def test_parse_station_status(self, mock_station_status_response):
        """Test parsing station status"""
        collector = CitiBikeCollector()
        statuses = collector.parse_station_status(mock_station_status_response)

        assert len(statuses) == 2
        assert statuses[0]["station_id"] == "test-station-1"
        assert statuses[0]["bikes_available"] == 12
        assert statuses[0]["docks_available"] == 36
        assert statuses[0]["bikes_disabled"] == 2
        assert statuses[0]["docks_disabled"] == 0
        assert isinstance(statuses[0]["timestamp"], datetime)

    @patch.object(CitiBikeCollector, "make_request")
    def test_collect_station_information(
        self, mock_request, mock_station_info_response
    ):
        """Test collecting station information"""
        mock_request.return_value = mock_station_info_response

        collector = CitiBikeCollector()
        data = collector.collect_station_information()

        assert data == mock_station_info_response
        assert len(data["data"]["stations"]) == 2

    @patch.object(CitiBikeCollector, "make_request")
    def test_collect_station_status(
        self, mock_request, mock_station_status_response
    ):
        """Test collecting station status"""
        mock_request.return_value = mock_station_status_response

        collector = CitiBikeCollector()
        data = collector.collect_station_status()

        assert data == mock_station_status_response
        assert len(data["data"]["stations"]) == 2

    def test_context_manager(self):
        """Test collector as context manager"""
        with CitiBikeCollector() as collector:
            assert collector.session is not None

        # Session should be closed after context exit
        # Note: We can't easily test this without implementation details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
