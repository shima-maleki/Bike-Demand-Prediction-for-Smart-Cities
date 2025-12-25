"""
OpenWeatherMap API Collector
Collects weather data for NYC bike stations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from src.data.collectors.base_collector import BaseCollector
from src.config.settings import get_settings

settings = get_settings()


class WeatherCollector(BaseCollector):
    """Collector for OpenWeatherMap API"""

    def __init__(self):
        """Initialize Weather collector"""
        super().__init__(
            base_url=settings.weather_api.base_url,
            timeout=settings.weather_api.timeout,
        )
        self.api_key = settings.weather_api.api_key
        self.units = settings.weather_api.units

    def collect_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Collect current weather for a location

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Weather data dictionary

        Example response:
        {
            "coord": {"lon": -73.9776, "lat": 40.7614},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
            "main": {
                "temp": 15.5,
                "feels_like": 14.2,
                "temp_min": 13.0,
                "temp_max": 17.0,
                "pressure": 1013,
                "humidity": 65
            },
            "visibility": 10000,
            "wind": {"speed": 4.5, "deg": 180},
            "rain": {"1h": 0},
            "dt": 1640000000,
            "timezone": -18000,
            "name": "New York"
        }
        """
        logger.debug(f"Collecting weather for ({lat}, {lon})")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": self.units,
        }

        data = self.make_request("weather", params=params)

        if self.validate_weather_data(data):
            return data
        else:
            raise ValueError(f"Invalid weather data for location ({lat}, {lon})")

    def collect_weather_for_area(
        self, center_lat: float, center_lon: float, count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Collect weather for multiple stations in an area

        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            count: Number of stations to get weather for

        Returns:
            List of weather data dictionaries
        """
        logger.info(f"Collecting weather for area around ({center_lat}, {center_lon})")

        params = {
            "lat": center_lat,
            "lon": center_lon,
            "cnt": count,
            "appid": self.api_key,
            "units": self.units,
        }

        try:
            data = self.make_request("find", params=params)
            weather_list = data.get("list", [])
            logger.info(f"Retrieved weather for {len(weather_list)} locations")
            return weather_list
        except Exception as e:
            logger.warning(f"Failed to get area weather, using single point: {e}")
            # Fallback to single point
            return [self.collect_current_weather(center_lat, center_lon)]

    def collect(self, lat: float = 40.7614, lon: float = -73.9776) -> Dict[str, Any]:
        """
        Collect weather data for NYC (default coordinates)

        Args:
            lat: Latitude (default: NYC center)
            lon: Longitude (default: NYC center)

        Returns:
            Weather data with collection metadata
        """
        logger.info("Starting weather data collection for NYC")

        weather_data = self.collect_current_weather(lat, lon)

        return {
            "weather_data": weather_data,
            "collection_timestamp": datetime.now().isoformat(),
            "location": {"lat": lat, "lon": lon},
        }

    def validate_weather_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate weather data

        Args:
            data: Weather data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(data, dict):
                logger.error("Weather data is not a dictionary")
                return False

            # Check required fields
            required_fields = ["main", "weather", "wind", "dt"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Check main weather metrics
            main = data["main"]
            required_main_fields = ["temp", "humidity", "pressure"]
            for field in required_main_fields:
                if field not in main:
                    logger.error(f"Missing main field: {field}")
                    return False

            # Check weather array
            if not isinstance(data["weather"], list) or len(data["weather"]) == 0:
                logger.error("Weather array is invalid")
                return False

            logger.debug("Weather data validation passed")
            return True

        except Exception as e:
            logger.error(f"Weather validation error: {e}")
            return False

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate collected data

        Args:
            data: Complete collected data

        Returns:
            True if valid, False otherwise
        """
        if "weather_data" not in data:
            logger.error("Missing weather_data in collected data")
            return False

        return self.validate_weather_data(data["weather_data"])

    def parse_weather_data(self, data: Dict[str, Any], location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse weather data into database format

        Args:
            data: Raw weather data from API
            location_id: Optional location identifier

        Returns:
            Parsed weather dictionary
        """
        timestamp = datetime.fromtimestamp(data.get("dt", datetime.now().timestamp()))

        main = data.get("main", {})
        wind = data.get("wind", {})
        weather_list = data.get("weather", [{}])
        weather_info = weather_list[0] if weather_list else {}
        rain = data.get("rain", {})
        coord = data.get("coord", {})

        parsed = {
            "timestamp": timestamp,
            "location_id": location_id or data.get("name", "NYC"),
            "latitude": coord.get("lat"),
            "longitude": coord.get("lon"),
            "temperature": float(main.get("temp", 0)),
            "feels_like": float(main.get("feels_like", 0)),
            "humidity": int(main.get("humidity", 0)),
            "pressure": int(main.get("pressure", 0)),
            "wind_speed": float(wind.get("speed", 0)),
            "precipitation": float(rain.get("1h", 0)),
            "weather_condition": weather_info.get("main", "Unknown"),
            "weather_description": weather_info.get("description", ""),
            "visibility": data.get("visibility"),
        }

        logger.debug(f"Parsed weather data for {parsed['location_id']}")
        return parsed

    def get_nyc_center_coordinates(self) -> tuple[float, float]:
        """
        Get NYC center coordinates for weather collection

        Returns:
            Tuple of (latitude, longitude)
        """
        # Times Square coordinates (center of Manhattan)
        return (40.7580, -73.9855)

    def collect_for_multiple_locations(
        self, locations: List[tuple[float, float, str]]
    ) -> List[Dict[str, Any]]:
        """
        Collect weather for multiple locations

        Args:
            locations: List of (lat, lon, location_id) tuples

        Returns:
            List of parsed weather records
        """
        weather_records = []

        for lat, lon, location_id in locations:
            try:
                data = self.collect_current_weather(lat, lon)
                parsed = self.parse_weather_data(data, location_id)
                weather_records.append(parsed)
            except Exception as e:
                logger.error(f"Failed to collect weather for {location_id}: {e}")
                continue

        logger.info(f"Collected weather for {len(weather_records)} locations")
        return weather_records
