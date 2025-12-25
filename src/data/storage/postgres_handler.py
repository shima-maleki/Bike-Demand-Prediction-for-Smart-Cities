"""
PostgreSQL Storage Handler
Handles all database operations for bike demand data
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from src.config.database import get_db_context, db_manager
from src.data.models import (
    BikeStation,
    BikeStationStatus,
    WeatherData,
    Feature,
    Prediction,
    ModelPerformance,
    DataQualityCheck,
)


class PostgreSQLHandler:
    """Handler for PostgreSQL database operations"""

    def __init__(self):
        """Initialize PostgreSQL handler"""
        self.db_manager = db_manager

    def upsert_stations(self, stations: List[Dict[str, Any]]) -> int:
        """
        Insert or update bike stations

        Args:
            stations: List of station dictionaries

        Returns:
            Number of stations upserted
        """
        try:
            with get_db_context() as db:
                count = 0
                for station_data in stations:
                    stmt = insert(BikeStation).values(**station_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["station_id"],
                        set_={
                            "name": stmt.excluded.name,
                            "latitude": stmt.excluded.latitude,
                            "longitude": stmt.excluded.longitude,
                            "capacity": stmt.excluded.capacity,
                            "is_active": stmt.excluded.is_active,
                            "updated_at": datetime.utcnow(),
                        },
                    )
                    db.execute(stmt)
                    count += 1

                db.commit()
                logger.info(f"Upserted {count} bike stations")
                return count

        except SQLAlchemyError as e:
            logger.error(f"Failed to upsert stations: {e}")
            raise

    def insert_station_statuses(self, statuses: List[Dict[str, Any]]) -> int:
        """
        Insert bike station statuses

        Args:
            statuses: List of status dictionaries

        Returns:
            Number of statuses inserted
        """
        try:
            with get_db_context() as db:
                status_objects = [BikeStationStatus(**status) for status in statuses]
                db.bulk_save_objects(status_objects)
                db.commit()
                logger.info(f"Inserted {len(statuses)} station statuses")
                return len(statuses)

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert station statuses: {e}")
            raise

    def insert_weather_data(self, weather_records: List[Dict[str, Any]]) -> int:
        """
        Insert weather data

        Args:
            weather_records: List of weather dictionaries

        Returns:
            Number of weather records inserted
        """
        try:
            with get_db_context() as db:
                weather_objects = [WeatherData(**record) for record in weather_records]
                db.bulk_save_objects(weather_objects)
                db.commit()
                logger.info(f"Inserted {len(weather_records)} weather records")
                return len(weather_records)

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert weather data: {e}")
            raise

    def get_latest_station_status(
        self, station_id: Optional[str] = None
    ) -> List[BikeStationStatus]:
        """
        Get latest status for stations

        Args:
            station_id: Optional specific station ID

        Returns:
            List of latest station statuses
        """
        try:
            with get_db_context() as db:
                if station_id:
                    query = (
                        select(BikeStationStatus)
                        .where(BikeStationStatus.station_id == station_id)
                        .order_by(desc(BikeStationStatus.timestamp))
                        .limit(1)
                    )
                    result = db.execute(query).scalar_one_or_none()
                    return [result] if result else []
                else:
                    # Get latest status for each station (using window function would be better)
                    query = (
                        select(BikeStationStatus)
                        .distinct(BikeStationStatus.station_id)
                        .order_by(BikeStationStatus.station_id, desc(BikeStationStatus.timestamp))
                    )
                    result = db.execute(query).scalars().all()
                    return list(result)

        except SQLAlchemyError as e:
            logger.error(f"Failed to get latest station status: {e}")
            raise

    def get_station_status_history(
        self,
        station_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[BikeStationStatus]:
        """
        Get historical status for a station

        Args:
            station_id: Station ID
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of historical station statuses
        """
        try:
            with get_db_context() as db:
                query = (
                    select(BikeStationStatus)
                    .where(
                        and_(
                            BikeStationStatus.station_id == station_id,
                            BikeStationStatus.timestamp >= start_time,
                            BikeStationStatus.timestamp <= end_time,
                        )
                    )
                    .order_by(BikeStationStatus.timestamp)
                )
                result = db.execute(query).scalars().all()
                return list(result)

        except SQLAlchemyError as e:
            logger.error(f"Failed to get station status history: {e}")
            raise

    def get_active_stations(self) -> List[BikeStation]:
        """
        Get all active bike stations

        Returns:
            List of active stations
        """
        try:
            with get_db_context() as db:
                query = select(BikeStation).where(BikeStation.is_active == True)
                result = db.execute(query).scalars().all()
                return list(result)

        except SQLAlchemyError as e:
            logger.error(f"Failed to get active stations: {e}")
            raise

    def get_station_by_id(self, station_id: str) -> Optional[BikeStation]:
        """
        Get station by ID

        Args:
            station_id: Station ID

        Returns:
            BikeStation object or None
        """
        try:
            with get_db_context() as db:
                query = select(BikeStation).where(BikeStation.station_id == station_id)
                result = db.execute(query).scalar_one_or_none()
                return result

        except SQLAlchemyError as e:
            logger.error(f"Failed to get station by ID: {e}")
            raise

    def insert_features(self, features: List[Dict[str, Any]]) -> int:
        """
        Insert engineered features

        Args:
            features: List of feature dictionaries

        Returns:
            Number of features inserted
        """
        try:
            with get_db_context() as db:
                feature_objects = [Feature(**feature) for feature in features]
                db.bulk_save_objects(feature_objects)
                db.commit()
                logger.info(f"Inserted {len(features)} feature records")
                return len(features)

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert features: {e}")
            raise

    def insert_predictions(self, predictions: List[Dict[str, Any]]) -> int:
        """
        Insert model predictions

        Args:
            predictions: List of prediction dictionaries

        Returns:
            Number of predictions inserted
        """
        try:
            with get_db_context() as db:
                prediction_objects = [Prediction(**pred) for pred in predictions]
                db.bulk_save_objects(prediction_objects)
                db.commit()
                logger.info(f"Inserted {len(predictions)} predictions")
                return len(predictions)

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert predictions: {e}")
            raise

    def insert_model_performance(self, performance: Dict[str, Any]) -> int:
        """
        Insert model performance metrics

        Args:
            performance: Performance metrics dictionary

        Returns:
            Performance record ID
        """
        try:
            with get_db_context() as db:
                perf_obj = ModelPerformance(**performance)
                db.add(perf_obj)
                db.commit()
                logger.info(f"Inserted model performance for {performance['model_name']}")
                return perf_obj.id

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert model performance: {e}")
            raise

    def insert_data_quality_check(self, check: Dict[str, Any]) -> int:
        """
        Insert data quality check result

        Args:
            check: Data quality check dictionary

        Returns:
            Check record ID
        """
        try:
            with get_db_context() as db:
                check_obj = DataQualityCheck(**check)
                db.add(check_obj)
                db.commit()
                logger.info(f"Inserted data quality check: {check['check_name']}")
                return check_obj.id

        except SQLAlchemyError as e:
            logger.error(f"Failed to insert data quality check: {e}")
            raise

    def get_data_quality_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get data quality summary for recent checks

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with quality summary
        """
        try:
            with get_db_context() as db:
                cutoff_time = datetime.utcnow() - datetime.timedelta(hours=hours)

                query = select(DataQualityCheck).where(
                    DataQualityCheck.check_timestamp >= cutoff_time
                )
                checks = db.execute(query).scalars().all()

                total = len(checks)
                passed = sum(1 for c in checks if c.status == "passed")
                failed = sum(1 for c in checks if c.status == "failed")

                return {
                    "total_checks": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": (passed / total * 100) if total > 0 else 0,
                }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get data quality summary: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Dictionary with database stats
        """
        try:
            stats = {}

            # Get table counts
            with get_db_context() as db:
                stats["bike_stations"] = db.query(BikeStation).count()
                stats["station_statuses"] = db.query(BikeStationStatus).count()
                stats["weather_records"] = db.query(WeatherData).count()
                stats["features"] = db.query(Feature).count()
                stats["predictions"] = db.query(Prediction).count()

            # Get table sizes
            stats["bike_stations_size"] = self.db_manager.get_table_size("bike_stations")
            stats["station_statuses_size"] = self.db_manager.get_table_size(
                "bike_station_status"
            )

            logger.info("Retrieved database statistics")
            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise


# Singleton instance
postgres_handler = PostgreSQLHandler()
