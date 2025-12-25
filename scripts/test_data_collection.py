"""
Test Data Collection Script
Manually test the Citi Bike data collection pipeline
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger
from src.data.collectors.citi_bike_collector import CitiBikeCollector
from src.data.storage.postgres_handler import postgres_handler
from src.data.processors.data_validator import DataValidator
import pandas as pd


def test_api_connection():
    """Test API connection and data retrieval"""
    logger.info("=" * 60)
    logger.info("Testing Citi Bike API Connection")
    logger.info("=" * 60)

    try:
        with CitiBikeCollector() as collector:
            # Test station information
            logger.info("\n1. Testing station information endpoint...")
            station_info = collector.collect_station_information()
            logger.info(f"✓ Successfully retrieved station information")
            logger.info(f"  - Total stations: {len(station_info['data']['stations'])}")
            logger.info(f"  - Last updated: {station_info.get('last_updated')}")

            # Test station status
            logger.info("\n2. Testing station status endpoint...")
            station_status = collector.collect_station_status()
            logger.info(f"✓ Successfully retrieved station status")
            logger.info(f"  - Total statuses: {len(station_status['data']['stations'])}")
            logger.info(f"  - Last updated: {station_status.get('last_updated')}")

            # Show sample data
            sample_station = station_info['data']['stations'][0]
            logger.info(f"\n3. Sample station information:")
            logger.info(f"  - ID: {sample_station.get('station_id')}")
            logger.info(f"  - Name: {sample_station.get('name')}")
            logger.info(f"  - Location: ({sample_station.get('lat')}, {sample_station.get('lon')})")
            logger.info(f"  - Capacity: {sample_station.get('capacity')}")

            sample_status = station_status['data']['stations'][0]
            logger.info(f"\n4. Sample station status:")
            logger.info(f"  - Station ID: {sample_status.get('station_id')}")
            logger.info(f"  - Bikes available: {sample_status.get('num_bikes_available')}")
            logger.info(f"  - Docks available: {sample_status.get('num_docks_available')}")

        logger.info("\n✅ API connection test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ API connection test FAILED: {e}")
        return False


def test_data_parsing():
    """Test data parsing functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Data Parsing")
    logger.info("=" * 60)

    try:
        with CitiBikeCollector() as collector:
            # Collect data
            station_info = collector.collect_station_information()
            station_status = collector.collect_station_status()

            # Parse station information
            logger.info("\n1. Parsing station information...")
            stations = collector.parse_station_information(station_info)
            logger.info(f"✓ Parsed {len(stations)} station records")
            logger.info(f"  - Sample: {stations[0]}")

            # Parse station status
            logger.info("\n2. Parsing station status...")
            statuses = collector.parse_station_status(station_status)
            logger.info(f"✓ Parsed {len(statuses)} status records")
            logger.info(f"  - Sample: {statuses[0]}")

        logger.info("\n✅ Data parsing test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Data parsing test FAILED: {e}")
        return False


def test_data_validation():
    """Test data validation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Data Validation")
    logger.info("=" * 60)

    try:
        with CitiBikeCollector() as collector:
            # Collect and parse data
            station_info = collector.collect_station_information()
            station_status = collector.collect_station_status()

            stations = collector.parse_station_information(station_info)
            statuses = collector.parse_station_status(station_status)

            # Create DataFrames
            stations_df = pd.DataFrame(stations)
            statuses_df = pd.DataFrame(statuses)

            # Validate
            validator = DataValidator()

            logger.info("\n1. Validating station information...")
            station_results = validator.validate_station_information(stations_df)
            logger.info(f"✓ Validation {'PASSED' if station_results['passed'] else 'FAILED'}")
            logger.info(f"  - Total checks: {len(station_results['checks'])}")
            logger.info(f"  - Passed: {sum(1 for c in station_results['checks'] if c['status'] == 'passed')}")

            logger.info("\n2. Validating station status...")
            status_results = validator.validate_station_status(statuses_df)
            logger.info(f"✓ Validation {'PASSED' if status_results['passed'] else 'FAILED'}")
            logger.info(f"  - Total checks: {len(status_results['checks'])}")
            logger.info(f"  - Passed: {sum(1 for c in status_results['checks'] if c['status'] == 'passed')}")

            # Show summary
            summary = validator.get_validation_summary()
            logger.info(f"\n3. Validation summary:")
            logger.info(f"  - Total validations: {summary['total_validations']}")
            logger.info(f"  - Passed: {summary['passed']}")
            logger.info(f"  - Failed: {summary['failed']}")
            logger.info(f"  - Pass rate: {summary['pass_rate']:.1f}%")

        logger.info("\n✅ Data validation test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Data validation test FAILED: {e}")
        return False


def test_database_storage():
    """Test database storage"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Database Storage")
    logger.info("=" * 60)

    try:
        with CitiBikeCollector() as collector:
            # Collect and parse data
            logger.info("\n1. Collecting data...")
            station_info = collector.collect_station_information()
            station_status = collector.collect_station_status()

            stations = collector.parse_station_information(station_info)
            statuses = collector.parse_station_status(station_status)

            # Store in database
            logger.info("\n2. Storing station information...")
            stations_count = postgres_handler.upsert_stations(stations[:10])  # Test with first 10
            logger.info(f"✓ Stored {stations_count} stations")

            logger.info("\n3. Storing station statuses...")
            statuses_count = postgres_handler.insert_station_statuses(statuses[:10])  # Test with first 10
            logger.info(f"✓ Stored {statuses_count} statuses")

            # Retrieve data
            logger.info("\n4. Retrieving data from database...")
            active_stations = postgres_handler.get_active_stations()
            logger.info(f"✓ Retrieved {len(active_stations)} active stations")

            latest_status = postgres_handler.get_latest_station_status()
            logger.info(f"✓ Retrieved latest status for {len(latest_status)} stations")

        logger.info("\n✅ Database storage test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Database storage test FAILED: {e}")
        logger.error(f"  Note: Make sure PostgreSQL is running (docker-compose up -d)")
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("CITI BIKE DATA COLLECTION PIPELINE TEST")
    logger.info("=" * 60)

    results = {
        "API Connection": test_api_connection(),
        "Data Parsing": test_data_parsing(),
        "Data Validation": test_data_validation(),
        "Database Storage": test_database_storage(),
    }

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

    total = len(results)
    passed = sum(results.values())
    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
