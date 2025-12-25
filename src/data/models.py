"""
SQLAlchemy Database Models
Defines ORM models for bike demand prediction data
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    DECIMAL,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class BikeStation(Base):
    """Bike station metadata table"""

    __tablename__ = "bike_stations"

    station_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    statuses = relationship("BikeStationStatus", back_populates="station", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="station", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="station", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BikeStation(id={self.station_id}, name={self.name})>"


class BikeStationStatus(Base):
    """Time-series bike station status data"""

    __tablename__ = "bike_station_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(50), ForeignKey("bike_stations.station_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    bikes_available = Column(Integer, nullable=False)
    docks_available = Column(Integer, nullable=False)
    bikes_disabled = Column(Integer, default=0)
    docks_disabled = Column(Integer, default=0)
    is_installed = Column(Boolean, default=True)
    is_renting = Column(Boolean, default=True)
    is_returning = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    station = relationship("BikeStation", back_populates="statuses")

    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_bike_station_status_station_timestamp", "station_id", "timestamp"),
        Index("idx_bike_station_status_timestamp_desc", timestamp.desc()),
    )

    def __repr__(self):
        return f"<BikeStationStatus(station={self.station_id}, time={self.timestamp}, bikes={self.bikes_available})>"


class WeatherData(Base):
    """Weather data table"""

    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    location_id = Column(String(50))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    temperature = Column(DECIMAL(5, 2))
    feels_like = Column(DECIMAL(5, 2))
    humidity = Column(Integer)
    wind_speed = Column(DECIMAL(5, 2))
    precipitation = Column(DECIMAL(5, 2), default=0)
    weather_condition = Column(String(50))
    weather_description = Column(String(255))
    pressure = Column(Integer)
    visibility = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_weather_data_timestamp_desc", timestamp.desc()),
        Index("idx_weather_data_location", "latitude", "longitude"),
    )

    def __repr__(self):
        return f"<WeatherData(time={self.timestamp}, temp={self.temperature}, condition={self.weather_condition})>"


class Feature(Base):
    """Engineered features table"""

    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(50), ForeignKey("bike_stations.station_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    feature_json = Column(JSONB, nullable=False)
    feature_version = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    station = relationship("BikeStation", back_populates="features")

    # Indexes
    __table_args__ = (
        Index("idx_features_station_timestamp", "station_id", "timestamp"),
        Index("idx_features_json", "feature_json", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<Feature(station={self.station_id}, version={self.feature_version}, time={self.timestamp})>"


class Prediction(Base):
    """Model predictions table"""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(50), ForeignKey("bike_stations.station_id", ondelete="CASCADE"), nullable=False)
    prediction_timestamp = Column(DateTime, nullable=False, index=True)
    predicted_demand = Column(DECIMAL(8, 2), nullable=False)
    model_version = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    confidence_interval_lower = Column(DECIMAL(8, 2))
    confidence_interval_upper = Column(DECIMAL(8, 2))
    prediction_horizon_hours = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    station = relationship("BikeStation", back_populates="predictions")

    # Indexes
    __table_args__ = (
        Index("idx_predictions_station_timestamp", "station_id", "prediction_timestamp"),
        Index("idx_predictions_model", "model_name", "model_version"),
        Index("idx_predictions_created_desc", created_at.desc()),
    )

    def __repr__(self):
        return f"<Prediction(station={self.station_id}, model={self.model_name}, demand={self.predicted_demand})>"


class ModelPerformance(Base):
    """Model performance metrics table"""

    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    evaluation_date = Column(DateTime, nullable=False, index=True)
    rmse = Column(DECIMAL(8, 4))
    mae = Column(DECIMAL(8, 4))
    mape = Column(DECIMAL(8, 4))
    r2_score = Column(DECIMAL(8, 4))
    data_drift_score = Column(DECIMAL(8, 4))
    prediction_drift_score = Column(DECIMAL(8, 4))
    model_metadata = Column("metadata", JSONB)  # Renamed to avoid SQLAlchemy reserved keyword
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_model_performance_model", "model_name", "model_version"),
        Index("idx_model_performance_date_desc", evaluation_date.desc()),
    )

    def __repr__(self):
        return f"<ModelPerformance(model={self.model_name}, rmse={self.rmse}, date={self.evaluation_date})>"


class DataQualityCheck(Base):
    """Data quality checks table"""

    __tablename__ = "data_quality_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_name = Column(String(100), nullable=False)
    table_name = Column(String(100), nullable=False)
    check_timestamp = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    expected_value = Column(JSONB)
    actual_value = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_data_quality_timestamp_desc", check_timestamp.desc()),
        Index("idx_data_quality_status", "status"),
    )

    def __repr__(self):
        return f"<DataQualityCheck(check={self.check_name}, status={self.status}, time={self.check_timestamp})>"


class APILog(Base):
    """API request logs table"""

    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(DECIMAL(10, 2))
    timestamp = Column(DateTime, nullable=False, index=True)
    client_ip = Column(String(50))
    user_agent = Column(Text)
    request_payload = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (Index("idx_api_logs_timestamp_desc", timestamp.desc()),)

    def __repr__(self):
        return f"<APILog(endpoint={self.endpoint}, status={self.status_code}, time={self.timestamp})>"
