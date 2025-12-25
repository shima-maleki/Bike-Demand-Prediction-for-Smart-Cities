"""
Manual Data Collection Script
Run data collection manually for Citi Bike stations
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger
from src.data.collectors.citi_bike_collector import CitiBikeCollector
from src.data.storage.postgres_handler import postgres_handler


def run_data_collection():
    """Run complete data collection pipeline"""
    logger.info("=" * 70)
    logger.info("CITI BIKE DATA COLLECTION - Manual Run")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    try:
        with CitiBikeCollector() as collector:
            # Step 1: Collect station information
            logger.info("\n[1/4] Collecting station information...")
            station_info_data = collector.collect_station_information()
            logger.info(f"✓ Retrieved {len(station_info_data['data']['stations'])} stations")

            # Step 2: Collect station status
            logger.info("\n[2/4] Collecting station status...")
            station_status_data = collector.collect_station_status()
            logger.info(f"✓ Retrieved {len(station_status_data['data']['stations'])} station statuses")

            # Step 3: Parse data
            logger.info("\n[3/4] Parsing data...")
            stations = collector.parse_station_information(station_info_data)
            statuses = collector.parse_station_status(station_status_data)
            logger.info(f"✓ Parsed {len(stations)} stations and {len(statuses)} statuses")

            # Step 4: Store in database
            logger.info("\n[4/4] Storing in database...")

            # Store stations
            logger.info("  - Upserting station information...")
            stations_count = postgres_handler.upsert_stations(stations)
            logger.info(f"  ✓ Stored {stations_count} stations")

            # Store statuses
            logger.info("  - Inserting station statuses...")
            statuses_count = postgres_handler.insert_station_statuses(statuses)
            logger.info(f"  ✓ Stored {statuses_count} statuses")

            # Log data quality check
            quality_check = {
                "check_name": "manual_data_collection",
                "table_name": "bike_station_status",
                "check_timestamp": datetime.utcnow(),
                "status": "passed",
                "expected_value": {"stations": "> 0", "statuses": "> 0"},
                "actual_value": {
                    "stations": stations_count,
                    "statuses": statuses_count
                },
                "error_message": None,
            }
            postgres_handler.insert_data_quality_check(quality_check)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("DATA COLLECTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Stations collected:  {stations_count}")
        logger.info(f"Statuses collected:  {statuses_count}")
        logger.info(f"Completed at:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        logger.info("\n✅ Data collection completed successfully!")

        # Show sample data
        logger.info("\n📊 Sample Data:")
        active_stations = postgres_handler.get_active_stations()
        logger.info(f"  - Total active stations in DB: {len(active_stations)}")

        latest_statuses = postgres_handler.get_latest_station_status()
        logger.info(f"  - Latest statuses available: {len(latest_statuses)}")

        if latest_statuses:
            sample = latest_statuses[0]
            logger.info(f"\n  Sample status:")
            logger.info(f"    Station: {sample.station.name if sample.station else sample.station_id}")
            logger.info(f"    Bikes available: {sample.bikes_available}")
            logger.info(f"    Docks available: {sample.docks_available}")
            logger.info(f"    Timestamp: {sample.timestamp}")

        return 0

    except Exception as e:
        logger.error(f"\n❌ Data collection failed: {e}")
        logger.error("  Make sure:")
        logger.error("  1. PostgreSQL is running (cd infrastructure && docker-compose up -d postgres)")
        logger.error("  2. Database schema is initialized")
        logger.error("  3. Network connection is available")
        return 1


if __name__ == "__main__":
    exit(run_data_collection())
