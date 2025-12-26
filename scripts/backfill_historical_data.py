#!/usr/bin/env python3
"""
Backfill historical Citi Bike data from NYC Open Data
Downloads last 3 months of trip data and reconstructs station availability
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from loguru import logger
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db_context
from src.data.models import BikeStationStatus
from sqlalchemy import text

def get_historical_trip_data_urls(months_back=3):
    """
    Generate URLs for Citi Bike historical data
    Data available at: https://s3.amazonaws.com/tripdata/
    Format: YYYYMM-citibike-tripdata.zip (note: NO .csv in middle)
    """
    urls = []
    base_url = "https://s3.amazonaws.com/tripdata"

    # Use specific months that are known to exist
    # Based on S3 bucket listing, most recent available: 202509, 202510, 202511
    # Start with just November (smallest file) to test pipeline
    months = ["202511"]  # Nov 2025 (667MB - smallest recent month)

    for month in months[:months_back]:
        filename = f"{month}-citibike-tripdata.zip"
        urls.append(f"{base_url}/{filename}")

    return urls

def download_and_process_month(url):
    """Download one month of data and process it

    Note: For months with >1M trips, the ZIP contains multiple CSVs
    We need to read and concatenate all of them
    """
    logger.info(f"Downloading: {url}")

    try:
        import zipfile
        import io

        # Download the ZIP file
        response = requests.get(url)
        response.raise_for_status()

        # Open ZIP file
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))

        # Get all CSV files in the ZIP
        csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
        logger.info(f"Found {len(csv_files)} CSV files in ZIP")

        # Read and concatenate all CSVs
        dfs = []
        for csv_file in csv_files:
            logger.info(f"Reading {csv_file}...")
            with zip_file.open(csv_file) as f:
                df = pd.read_csv(f)
                dfs.append(df)

        # Combine all dataframes
        df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Downloaded {len(df)} total trip records")

        # Convert timestamps
        df['started_at'] = pd.to_datetime(df['started_at'])
        df['ended_at'] = pd.to_datetime(df['ended_at'])

        return df

    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return None

def reconstruct_station_availability(trip_df):
    """
    Reconstruct station availability from trip data
    
    Logic:
    - Each trip START decreases bikes_available at start station
    - Each trip END increases bikes_available at end station
    """
    logger.info("Reconstructing station availability patterns...")
    
    # Get unique stations
    start_stations = trip_df[['start_station_id', 'start_station_name']].rename(
        columns={'start_station_id': 'station_id', 'start_station_name': 'station_name'}
    )
    end_stations = trip_df[['end_station_id', 'end_station_name']].rename(
        columns={'end_station_id': 'station_id', 'end_station_name': 'station_name'}
    )
    
    all_stations = pd.concat([start_stations, end_stations]).drop_duplicates('station_id')
    
    logger.info(f"Found {len(all_stations)} unique stations")
    
    # Group trips by hour to simulate availability snapshots
    trip_df['hour'] = trip_df['started_at'].dt.floor('H')
    
    # Count departures (bikes leaving) per station per hour
    departures = trip_df.groupby(['start_station_id', 'hour']).size().reset_index(name='departures')
    
    # Count arrivals (bikes arriving) per station per hour
    arrivals = trip_df.groupby(['end_station_id', 'hour']).size().reset_index(name='arrivals')
    
    # Merge to get net change
    activity = pd.merge(
        departures.rename(columns={'start_station_id': 'station_id'}),
        arrivals.rename(columns={'end_station_id': 'station_id'}),
        on=['station_id', 'hour'],
        how='outer'
    ).fillna(0)
    
    # Estimate bikes_available (starting from assumed capacity of 20)
    activity['bikes_available'] = 20 - activity['departures'] + activity['arrivals']
    activity['bikes_available'] = activity['bikes_available'].clip(0, 30)
    activity['docks_available'] = 30 - activity['bikes_available']
    
    logger.info(f"Reconstructed {len(activity)} hourly snapshots")
    
    return activity

def register_historical_stations(activity_df):
    """Register historical stations that don't exist in bike_stations table"""
    logger.info("Registering historical stations...")

    # Get unique stations from historical data
    unique_stations = activity_df['station_id'].unique()
    logger.info(f"Found {len(unique_stations)} unique stations in historical data")

    with get_db_context() as db:
        registered = 0

        for station_id in unique_stations:
            try:
                # Check if station already exists
                exists = db.execute(
                    text("SELECT 1 FROM bike_stations WHERE station_id = :station_id"),
                    {"station_id": str(station_id)}
                ).fetchone()

                if not exists:
                    # Insert placeholder station record
                    db.execute(
                        text("""
                            INSERT INTO bike_stations
                            (station_id, name, latitude, longitude, capacity, is_active, created_at, updated_at)
                            VALUES
                            (:station_id, :name, 0.0, 0.0, 30, false, NOW(), NOW())
                            ON CONFLICT (station_id) DO NOTHING
                        """),
                        {
                            "station_id": str(station_id),
                            "name": f"Historical Station {station_id}"
                        }
                    )
                    registered += 1

                    if registered % 100 == 0:
                        db.commit()
                        logger.info(f"Registered {registered} historical stations...")

            except Exception as e:
                logger.error(f"Failed to register station {station_id}: {e}")
                continue

        db.commit()
        logger.info(f"✓ Registered {registered} new historical stations")

def insert_historical_data(activity_df, max_records=50000):
    """Insert reconstructed data into database (limited to max_records)"""
    logger.info(f"Inserting historical data into database (max {max_records} records)...")

    # First, register all historical stations
    register_historical_stations(activity_df)

    # Limit the dataframe to max_records
    df_to_insert = activity_df.head(max_records)
    logger.info(f"Will insert {len(df_to_insert)} records")

    with get_db_context() as db:
        inserted = 0

        for _, row in df_to_insert.iterrows():
            try:
                # Insert status record
                db.execute(
                    text("""
                        INSERT INTO bike_station_status
                        (station_id, timestamp, bikes_available, docks_available,
                         bikes_disabled, docks_disabled, is_installed, is_renting, is_returning, created_at)
                        VALUES
                        (:station_id, :timestamp, :bikes_available, :docks_available,
                         0, 0, true, true, true, NOW())
                        ON CONFLICT (station_id, timestamp) DO NOTHING
                    """),
                    {
                        "station_id": str(row['station_id']),
                        "timestamp": row['hour'],
                        "bikes_available": int(row['bikes_available']),
                        "docks_available": int(row['docks_available'])
                    }
                )
                inserted += 1

                if inserted % 1000 == 0:
                    logger.info(f"Inserted {inserted} records...")
                    db.commit()

            except Exception as e:
                logger.error(f"Failed to insert record: {e}")
                continue

        db.commit()
        logger.info(f"✓ Total inserted: {inserted} historical records")

def backfill_historical_weather():
    """
    Backfill historical weather data
    Using Visual Crossing Weather API (free tier: 1000 calls/day)
    """
    logger.info("Backfilling historical weather data...")
    
    # TODO: Implement historical weather backfill
    # Options:
    # 1. Visual Crossing API: https://www.visualcrossing.com/weather-api
    # 2. NOAA Climate Data: https://www.ncdc.noaa.gov/cdo-web/
    # 3. Open-Meteo Historical: https://open-meteo.com/
    
    logger.warning("Historical weather backfill not implemented yet")
    logger.info("Using manual approach: Query weather APIs for past dates")

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("BACKFILLING HISTORICAL DATA (Last 3 Months)")
    logger.info("=" * 70)
    
    # Get URLs for last 3 months
    urls = get_historical_trip_data_urls(months_back=3)
    
    logger.info(f"Will download {len(urls)} months of data:")
    for url in urls:
        logger.info(f"  - {url}")
    
    # Process each month
    all_activity = []
    
    for url in urls:
        trip_data = download_and_process_month(url)
        
        if trip_data is not None:
            activity = reconstruct_station_availability(trip_data)
            all_activity.append(activity)
    
    if all_activity:
        # Combine all months
        combined_activity = pd.concat(all_activity, ignore_index=True)
        logger.info(f"Total activity records: {len(combined_activity)}")
        
        # Insert into database
        insert_historical_data(combined_activity)
        
        logger.success("✓ Historical data backfill complete!")
        
        # Show summary
        with get_db_context() as db:
            result = db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest,
                        COUNT(DISTINCT station_id) as unique_stations
                    FROM bike_station_status
                """)
            ).fetchone()
            
            logger.info("=" * 70)
            logger.info("DATABASE SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Total records: {result[0]}")
            logger.info(f"Date range: {result[1]} to {result[2]}")
            logger.info(f"Unique stations: {result[3]}")
    
    else:
        logger.error("No data downloaded successfully")
        sys.exit(1)
