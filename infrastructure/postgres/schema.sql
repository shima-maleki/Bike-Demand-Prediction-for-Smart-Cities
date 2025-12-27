-- Bike Demand Prediction Database Schema
-- PostgreSQL database schema for time-series bike demand forecasting

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create bike_stations table
CREATE TABLE IF NOT EXISTS bike_stations (
    station_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    capacity INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on station location for geo queries
CREATE INDEX IF NOT EXISTS idx_bike_stations_location ON bike_stations (latitude, longitude);

-- Create bike_station_status table (time-series data)
CREATE TABLE IF NOT EXISTS bike_station_status (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    bikes_available INTEGER NOT NULL,
    docks_available INTEGER NOT NULL,
    bikes_disabled INTEGER DEFAULT 0,
    docks_disabled INTEGER DEFAULT 0,
    is_installed BOOLEAN DEFAULT TRUE,
    is_renting BOOLEAN DEFAULT TRUE,
    is_returning BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE
);

-- Create indexes for time-series queries
CREATE INDEX IF NOT EXISTS idx_bike_station_status_station_id ON bike_station_status (station_id);
CREATE INDEX IF NOT EXISTS idx_bike_station_status_timestamp ON bike_station_status (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bike_station_status_station_timestamp ON bike_station_status (station_id, timestamp DESC);

-- Create weather_data table (time-series data)
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    location_id VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    temperature DECIMAL(5, 2),
    feels_like DECIMAL(5, 2),
    humidity INTEGER,
    wind_speed DECIMAL(5, 2),
    precipitation DECIMAL(5, 2) DEFAULT 0,
    weather_condition VARCHAR(50),
    weather_description VARCHAR(255),
    pressure INTEGER,
    visibility INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on weather timestamp
CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_weather_data_location ON weather_data (latitude, longitude);

-- Create features table (engineered features)
CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    feature_json JSONB NOT NULL,
    feature_version VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE,
    UNIQUE (station_id, timestamp, feature_version)  -- Allow ON CONFLICT for upserts
);

-- Create indexes for feature queries
CREATE INDEX IF NOT EXISTS idx_features_station_id ON features (station_id);
CREATE INDEX IF NOT EXISTS idx_features_timestamp ON features (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_features_version ON features (feature_version);
CREATE INDEX IF NOT EXISTS idx_features_json ON features USING GIN (feature_json);

-- Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMP NOT NULL,
    predicted_demand DECIMAL(8, 2) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    confidence_interval_lower DECIMAL(8, 2),
    confidence_interval_upper DECIMAL(8, 2),
    prediction_horizon_hours INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES bike_stations(station_id) ON DELETE CASCADE
);

-- Create indexes for prediction queries
CREATE INDEX IF NOT EXISTS idx_predictions_station_id ON predictions (station_id);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions (prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions (model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);

-- Create model_performance table
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    evaluation_date DATE NOT NULL,
    rmse DECIMAL(8, 4),
    mae DECIMAL(8, 4),
    mape DECIMAL(8, 4),
    r2_score DECIMAL(8, 4),
    data_drift_score DECIMAL(8, 4),
    prediction_drift_score DECIMAL(8, 4),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for model performance tracking
CREATE INDEX IF NOT EXISTS idx_model_performance_model ON model_performance (model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_model_performance_date ON model_performance (evaluation_date DESC);

-- Create data_quality_checks table
CREATE TABLE IF NOT EXISTS data_quality_checks (
    id SERIAL PRIMARY KEY,
    check_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    check_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    expected_value JSONB,
    actual_value JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for data quality queries
CREATE INDEX IF NOT EXISTS idx_data_quality_checks_timestamp ON data_quality_checks (check_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_checks_status ON data_quality_checks (status);

-- Create api_logs table for monitoring
CREATE TABLE IF NOT EXISTS api_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms DECIMAL(10, 2),
    timestamp TIMESTAMP NOT NULL,
    client_ip VARCHAR(50),
    user_agent TEXT,
    request_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for API log queries
CREATE INDEX IF NOT EXISTS idx_api_logs_timestamp ON api_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_logs (endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_status ON api_logs (status_code);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to bike_stations table
CREATE TRIGGER update_bike_stations_updated_at
    BEFORE UPDATE ON bike_stations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for latest station status
CREATE OR REPLACE VIEW latest_station_status AS
SELECT DISTINCT ON (station_id)
    bss.station_id,
    bs.name,
    bs.latitude,
    bs.longitude,
    bs.capacity,
    bss.bikes_available,
    bss.docks_available,
    bss.bikes_disabled,
    bss.docks_disabled,
    bss.timestamp,
    (bss.bikes_available::DECIMAL / NULLIF(bs.capacity, 0)) * 100 AS occupancy_percentage
FROM bike_station_status bss
JOIN bike_stations bs ON bss.station_id = bs.station_id
WHERE bs.is_active = TRUE
ORDER BY bss.station_id, bss.timestamp DESC;

-- Create view for hourly aggregated demand
CREATE OR REPLACE VIEW hourly_demand AS
SELECT
    station_id,
    DATE_TRUNC('hour', timestamp) AS hour,
    AVG(bikes_available) AS avg_bikes_available,
    MIN(bikes_available) AS min_bikes_available,
    MAX(bikes_available) AS max_bikes_available,
    STDDEV(bikes_available) AS stddev_bikes_available,
    COUNT(*) AS num_observations
FROM bike_station_status
GROUP BY station_id, DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

-- Create materialized view for daily statistics (for performance)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_station_stats AS
SELECT
    station_id,
    DATE(timestamp) AS date,
    AVG(bikes_available) AS avg_bikes_available,
    MIN(bikes_available) AS min_bikes_available,
    MAX(bikes_available) AS max_bikes_available,
    STDDEV(bikes_available) AS stddev_bikes_available,
    COUNT(*) AS num_observations
FROM bike_station_status
GROUP BY station_id, DATE(timestamp);

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_daily_station_stats_station_date
ON daily_station_stats (station_id, date DESC);

-- Grant permissions (will be updated with actual user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bike_demand_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bike_demand_user;
