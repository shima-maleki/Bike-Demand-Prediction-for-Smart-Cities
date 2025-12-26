#!/usr/bin/env python3
"""
Backfill historical weather data using Open-Meteo API (free, no API key needed)
For the period: Oct 31 - Dec 26, 2025
"""

import requests
import pandas as pd
from datetime import datetime
from loguru import logger
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db_context
from sqlalchemy import text

def backfill_weather_data(start_date="2025-10-31", end_date="2025-12-26"):
    """
    Backfill weather data using Open-Meteo Historical Weather API

    NYC coordinates: 40.7128°N, 74.0060°W
    API: https://open-meteo.com/en/docs/historical-weather-api
    """
    logger.info("=" * 70)
    logger.info("BACKFILLING HISTORICAL WEATHER DATA")
    logger.info("=" * 70)
    logger.info(f"Period: {start_date} to {end_date}")

    # NYC coordinates (Central Park)
    latitude = 40.7829
    longitude = -73.9654

    # Open-Meteo API endpoint
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "weather_code"
        ],
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "America/New_York"
    }

    logger.info("Fetching weather data from Open-Meteo API...")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Parse hourly data
        hourly = data['hourly']

        df = pd.DataFrame({
            'timestamp': pd.to_datetime(hourly['time']),
            'temperature': hourly['temperature_2m'],
            'humidity': hourly['relative_humidity_2m'],
            'precipitation': hourly['precipitation'],
            'wind_speed': hourly['wind_speed_10m'],
            'weather_code': hourly['weather_code']
        })

        logger.info(f"✓ Fetched {len(df)} hourly weather records")

        # Map weather codes to conditions
        # WMO Weather interpretation codes
        weather_mapping = {
            0: 'Clear',
            1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
            45: 'Foggy', 48: 'Foggy',
            51: 'Light Drizzle', 53: 'Moderate Drizzle', 55: 'Dense Drizzle',
            61: 'Slight Rain', 63: 'Moderate Rain', 65: 'Heavy Rain',
            71: 'Slight Snow', 73: 'Moderate Snow', 75: 'Heavy Snow',
            80: 'Slight Rain Showers', 81: 'Moderate Rain Showers', 82: 'Violent Rain Showers',
            95: 'Thunderstorm', 96: 'Thunderstorm with Hail', 99: 'Thunderstorm with Heavy Hail'
        }

        df['weather_condition'] = df['weather_code'].map(weather_mapping).fillna('Unknown')

        # Insert into database
        logger.info("Inserting weather data into database...")

        with get_db_context() as db:
            inserted = 0

            for _, row in df.iterrows():
                try:
                    db.execute(
                        text("""
                            INSERT INTO weather_data
                            (timestamp, temperature, humidity, wind_speed, precipitation, weather_condition, created_at)
                            VALUES
                            (:timestamp, :temperature, :humidity, :wind_speed, :precipitation, :weather_condition, NOW())
                            ON CONFLICT (timestamp) DO UPDATE SET
                                temperature = EXCLUDED.temperature,
                                humidity = EXCLUDED.humidity,
                                wind_speed = EXCLUDED.wind_speed,
                                precipitation = EXCLUDED.precipitation,
                                weather_condition = EXCLUDED.weather_condition
                        """),
                        {
                            "timestamp": row['timestamp'],
                            "temperature": float(row['temperature']) if pd.notna(row['temperature']) else None,
                            "humidity": float(row['humidity']) if pd.notna(row['humidity']) else None,
                            "wind_speed": float(row['wind_speed']) if pd.notna(row['wind_speed']) else None,
                            "precipitation": float(row['precipitation']) if pd.notna(row['precipitation']) else None,
                            "weather_condition": str(row['weather_condition'])
                        }
                    )
                    inserted += 1

                    if inserted % 100 == 0:
                        logger.info(f"Inserted {inserted} weather records...")
                        db.commit()

                except Exception as e:
                    logger.error(f"Failed to insert weather record: {e}")
                    continue

            db.commit()
            logger.info(f"✓ Total inserted: {inserted} weather records")

        # Verify
        with get_db_context() as db:
            result = db.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest
                    FROM weather_data
                """)
            ).fetchone()

            logger.info("=" * 70)
            logger.info("WEATHER DATA SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Total records: {result[0]}")
            logger.info(f"Date range: {result[1]} to {result[2]}")

        logger.success("✓ Weather data backfill complete!")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch weather data: {e}")
        return False

if __name__ == "__main__":
    # Get date range from bike_station_status table
    with get_db_context() as db:
        result = db.execute(
            text("SELECT MIN(timestamp)::date, MAX(timestamp)::date FROM bike_station_status")
        ).fetchone()

        start_date = str(result[0])
        end_date = str(result[1])

    logger.info(f"Backfilling weather for period: {start_date} to {end_date}")

    success = backfill_weather_data(start_date, end_date)

    if not success:
        sys.exit(1)
