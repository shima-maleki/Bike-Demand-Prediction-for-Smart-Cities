"""
Citi Bike API Collector
Collects bike station information and real-time status from NYC Citi Bike GBFS API
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from src.data.collectors.base_collector import BaseCollector
from src.config.settings import get_settings

settings = get_settings()


class CitiBikeCollector(BaseCollector):
    """Collector for NYC Citi Bike GBFS (General Bikeshare Feed Specification) API"""

    def __init__(self):
        """Initialize Citi Bike collector"""
        super().__init__(
            base_url=settings.citibike_api.base_url,
            timeout=settings.citibike_api.timeout,
        )
        self.station_info_url = settings.citibike_api.station_information_url
        self.station_status_url = settings.citibike_api.station_status_url

    def collect_station_information(self) -> Dict[str, Any]:
        """
        Collect station information (static data: location, capacity)

        Returns:
            Dictionary containing station information

        Example response structure:
        {
            "data": {
                "stations": [
                    {
                        "station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c",
                        "name": "W 52 St & 11 Ave",
                        "lat": 40.76727216,
                        "lon": -73.99392888,
                        "capacity": 55,
                        "region_id": "71",
                        "rental_methods": ["KEY", "CREDITCARD"],
                        "electric_bike_surcharge_waiver": false,
                        "eightd_has_key_dispenser": false,
                        "has_kiosk": true
                    }
                ]
            },
            "last_updated": 1640000000,
            "ttl": 10
        }
        """
        logger.info("Collecting Citi Bike station information")
        data = self.make_request(self.station_info_url)

        if self.validate_station_information(data):
            logger.info(f"Successfully collected {len(data.get('data', {}).get('stations', []))} stations")
            return data
        else:
            raise ValueError("Invalid station information data")

    def collect_station_status(self) -> Dict[str, Any]:
        """
        Collect real-time station status (bikes available, docks available)

        Returns:
            Dictionary containing station status

        Example response structure:
        {
            "data": {
                "stations": [
                    {
                        "station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c",
                        "num_bikes_available": 12,
                        "num_bikes_disabled": 3,
                        "num_docks_available": 40,
                        "num_docks_disabled": 0,
                        "is_installed": 1,
                        "is_renting": 1,
                        "is_returning": 1,
                        "last_reported": 1640000000,
                        "num_ebikes_available": 5,
                        "eightd_has_available_keys": false
                    }
                ]
            },
            "last_updated": 1640000000,
            "ttl": 10
        }
        """
        logger.info("Collecting Citi Bike station status")
        data = self.make_request(self.station_status_url)

        if self.validate_station_status(data):
            logger.info(f"Successfully collected status for {len(data.get('data', {}).get('stations', []))} stations")
            return data
        else:
            raise ValueError("Invalid station status data")

    def collect(self) -> Dict[str, Any]:
        """
        Collect both station information and status

        Returns:
            Dictionary with both station info and status
        """
        logger.info("Starting Citi Bike data collection")

        station_info = self.collect_station_information()
        station_status = self.collect_station_status()

        return {
            "station_information": station_info,
            "station_status": station_status,
            "collection_timestamp": datetime.now().isoformat(),
        }

    def validate_station_information(self, data: Dict[str, Any]) -> bool:
        """
        Validate station information data

        Args:
            data: Station information data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(data, dict):
                logger.error("Data is not a dictionary")
                return False

            if "data" not in data:
                logger.error("Missing 'data' key in response")
                return False

            if "stations" not in data["data"]:
                logger.error("Missing 'stations' key in data")
                return False

            stations = data["data"]["stations"]
            if not isinstance(stations, list) or len(stations) == 0:
                logger.error("Stations is not a non-empty list")
                return False

            # Validate required fields in first station
            required_fields = ["station_id", "name", "lat", "lon", "capacity"]
            first_station = stations[0]

            for field in required_fields:
                if field not in first_station:
                    logger.error(f"Missing required field: {field}")
                    return False

            logger.debug("Station information validation passed")
            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def validate_station_status(self, data: Dict[str, Any]) -> bool:
        """
        Validate station status data

        Args:
            data: Station status data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(data, dict):
                logger.error("Data is not a dictionary")
                return False

            if "data" not in data:
                logger.error("Missing 'data' key in response")
                return False

            if "stations" not in data["data"]:
                logger.error("Missing 'stations' key in data")
                return False

            stations = data["data"]["stations"]
            if not isinstance(stations, list) or len(stations) == 0:
                logger.error("Stations is not a non-empty list")
                return False

            # Validate required fields in first station
            required_fields = [
                "station_id",
                "num_bikes_available",
                "num_docks_available",
            ]
            first_station = stations[0]

            for field in required_fields:
                if field not in first_station:
                    logger.error(f"Missing required field: {field}")
                    return False

            logger.debug("Station status validation passed")
            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate collected data

        Args:
            data: Complete collected data

        Returns:
            True if valid, False otherwise
        """
        if "station_information" not in data or "station_status" not in data:
            logger.error("Missing station_information or station_status in data")
            return False

        return (
            self.validate_station_information(data["station_information"])
            and self.validate_station_status(data["station_status"])
        )

    def parse_station_information(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse station information into a list of station records

        Args:
            data: Raw station information data

        Returns:
            List of parsed station dictionaries
        """
        stations = []

        for station in data["data"]["stations"]:
            parsed_station = {
                "station_id": station["station_id"],
                "name": station["name"],
                "latitude": float(station["lat"]),
                "longitude": float(station["lon"]),
                "capacity": int(station["capacity"]),
                "is_active": True,  # Assuming active if in feed
            }
            stations.append(parsed_station)

        logger.info(f"Parsed {len(stations)} station information records")
        return stations

    def parse_station_status(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse station status into a list of status records

        Args:
            data: Raw station status data

        Returns:
            List of parsed status dictionaries
        """
        statuses = []
        timestamp = datetime.fromtimestamp(data.get("last_updated", datetime.now().timestamp()))

        for station in data["data"]["stations"]:
            parsed_status = {
                "station_id": station["station_id"],
                "timestamp": timestamp,
                "bikes_available": int(station["num_bikes_available"]),
                "docks_available": int(station["num_docks_available"]),
                "bikes_disabled": int(station.get("num_bikes_disabled", 0)),
                "docks_disabled": int(station.get("num_docks_disabled", 0)),
                "is_installed": bool(station.get("is_installed", 1)),
                "is_renting": bool(station.get("is_renting", 1)),
                "is_returning": bool(station.get("is_returning", 1)),
            }
            statuses.append(parsed_status)

        logger.info(f"Parsed {len(statuses)} station status records")
        return statuses

    def get_active_stations_count(self) -> int:
        """
        Get count of active stations

        Returns:
            Number of active stations
        """
        try:
            data = self.collect_station_information()
            return len(data.get("data", {}).get("stations", []))
        except Exception as e:
            logger.error(f"Failed to get active stations count: {e}")
            return 0
