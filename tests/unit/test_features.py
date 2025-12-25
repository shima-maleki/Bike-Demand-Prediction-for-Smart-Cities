"""
Unit Tests for Feature Engineering
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.features.temporal_features import TemporalFeatureGenerator
from src.features.lag_features import LagFeatureGenerator
from src.features.rolling_features import RollingFeatureGenerator
from src.features.weather_features import WeatherFeatureGenerator
from src.features.holiday_features import HolidayFeatureGenerator


@pytest.fixture
def sample_bike_data():
    """Create sample bike data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="h")

    df = pd.DataFrame({
        "station_id": "station_1",
        "timestamp": dates,
        "bikes_available": np.random.randint(0, 30, 100),
        "docks_available": np.random.randint(0, 20, 100)
    })

    return df


@pytest.fixture
def sample_weather_data():
    """Create sample weather data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="h")

    df = pd.DataFrame({
        "timestamp": dates,
        "temperature": np.random.uniform(10, 25, 100),
        "humidity": np.random.randint(40, 90, 100),
        "wind_speed": np.random.uniform(0, 10, 100),
        "precipitation": np.random.choice([0, 0, 0, 0.5, 2.0], 100),
        "weather_condition": np.random.choice(["Clear", "Clouds", "Rain"], 100),
        "feels_like": np.random.uniform(8, 23, 100),
        "visibility": np.random.randint(5000, 10000, 100),
        "pressure": np.random.randint(1000, 1030, 100)
    })

    return df


class TestTemporalFeatures:
    """Test temporal feature generation"""

    def test_temporal_features_generated(self, sample_bike_data):
        """Test that temporal features are generated"""
        generator = TemporalFeatureGenerator()
        result = generator.generate(sample_bike_data)

        # Check that features were added
        assert len(result.columns) > len(sample_bike_data.columns)

        # Check specific features exist
        assert "hour_of_day" in result.columns
        assert "day_of_week" in result.columns
        assert "is_weekend" in result.columns
        assert "season" in result.columns

    def test_hour_of_day_range(self, sample_bike_data):
        """Test that hour_of_day is in valid range"""
        generator = TemporalFeatureGenerator()
        result = generator.generate(sample_bike_data)

        assert result["hour_of_day"].min() >= 0
        assert result["hour_of_day"].max() <= 23

    def test_day_of_week_range(self, sample_bike_data):
        """Test that day_of_week is in valid range"""
        generator = TemporalFeatureGenerator()
        result = generator.generate(sample_bike_data)

        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 6

    def test_is_weekend_binary(self, sample_bike_data):
        """Test that is_weekend is binary"""
        generator = TemporalFeatureGenerator()
        result = generator.generate(sample_bike_data)

        assert set(result["is_weekend"].unique()).issubset({0, 1})

    def test_cyclic_encoding(self, sample_bike_data):
        """Test that cyclic encoding is within bounds"""
        generator = TemporalFeatureGenerator()
        result = generator.generate(sample_bike_data)

        assert "hour_sin" in result.columns
        assert "hour_cos" in result.columns

        assert result["hour_sin"].min() >= -1
        assert result["hour_sin"].max() <= 1
        assert result["hour_cos"].min() >= -1
        assert result["hour_cos"].max() <= 1


class TestLagFeatures:
    """Test lag feature generation"""

    def test_lag_features_generated(self, sample_bike_data):
        """Test that lag features are generated"""
        generator = LagFeatureGenerator(
            lag_hours=[1, 3, 6],
            target_column="bikes_available"
        )
        result = generator.generate(sample_bike_data)

        # Check that lag features exist
        assert "bikes_available_lag_1h" in result.columns
        assert "bikes_available_lag_3h" in result.columns
        assert "bikes_available_lag_6h" in result.columns

    def test_lag_values_correct(self, sample_bike_data):
        """Test that lag values are correctly shifted"""
        generator = LagFeatureGenerator(
            lag_hours=[1],
            target_column="bikes_available"
        )
        result = generator.generate(sample_bike_data)

        # Value at index 10 should match value at index 9 in lag_1h
        assert result.loc[10, "bikes_available_lag_1h"] == result.loc[9, "bikes_available"]

    def test_change_features(self, sample_bike_data):
        """Test that change features are calculated"""
        generator = LagFeatureGenerator(
            lag_hours=[1],
            target_column="bikes_available"
        )
        result = generator.generate(sample_bike_data)

        assert "bikes_available_change_1h" in result.columns
        assert "bikes_available_pct_change_1h" in result.columns


class TestRollingFeatures:
    """Test rolling window features"""

    def test_rolling_features_generated(self, sample_bike_data):
        """Test that rolling features are generated"""
        generator = RollingFeatureGenerator(
            windows=[3, 6],
            statistics=["mean", "std"],
            target_column="bikes_available"
        )
        result = generator.generate(sample_bike_data)

        assert "bikes_available_rolling_mean_3h" in result.columns
        assert "bikes_available_rolling_std_3h" in result.columns
        assert "bikes_available_rolling_mean_6h" in result.columns

    def test_rolling_mean_calculation(self, sample_bike_data):
        """Test that rolling mean is calculated correctly"""
        generator = RollingFeatureGenerator(
            windows=[3],
            statistics=["mean"],
            target_column="bikes_available"
        )
        result = generator.generate(sample_bike_data)

        # Check a specific value
        idx = 10
        expected_mean = sample_bike_data.loc[8:10, "bikes_available"].mean()
        actual_mean = result.loc[idx, "bikes_available_rolling_mean_3h"]

        assert abs(expected_mean - actual_mean) < 0.01


class TestWeatherFeatures:
    """Test weather feature generation"""

    def test_weather_features_generated(self, sample_weather_data):
        """Test that weather features are generated"""
        generator = WeatherFeatureGenerator()
        result = generator.generate(sample_weather_data)

        assert len(result.columns) > len(sample_weather_data.columns)

        # Check specific features
        assert "temperature_normalized" in result.columns
        assert "is_rainy" in result.columns
        assert "wind_category" in result.columns

    def test_temperature_normalized_range(self, sample_weather_data):
        """Test that normalized temperature is in [0, 1]"""
        generator = WeatherFeatureGenerator()
        result = generator.generate(sample_weather_data)

        assert result["temperature_normalized"].min() >= 0
        assert result["temperature_normalized"].max() <= 1

    def test_is_rainy_binary(self, sample_weather_data):
        """Test that is_rainy is binary"""
        generator = WeatherFeatureGenerator()
        result = generator.generate(sample_weather_data)

        assert set(result["is_rainy"].unique()).issubset({0, 1})

    def test_weather_severity_range(self, sample_weather_data):
        """Test that weather severity is in valid range"""
        generator = WeatherFeatureGenerator()
        result = generator.generate(sample_weather_data)

        if "weather_severity" in result.columns:
            assert result["weather_severity"].min() >= 0
            assert result["weather_severity"].max() <= 5


class TestHolidayFeatures:
    """Test holiday feature generation"""

    def test_holiday_features_generated(self):
        """Test that holiday features are generated"""
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "value": np.random.randn(len(dates))
        })

        generator = HolidayFeatureGenerator(country="US", state="NY")
        result = generator.generate(df)

        assert "is_holiday" in result.columns
        assert "is_holiday_eve" in result.columns
        assert "days_to_next_holiday" in result.columns

    def test_is_holiday_binary(self):
        """Test that is_holiday is binary"""
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "value": np.random.randn(len(dates))
        })

        generator = HolidayFeatureGenerator(country="US", state="NY")
        result = generator.generate(df)

        assert set(result["is_holiday"].unique()).issubset({0, 1})

    def test_new_years_detected(self):
        """Test that New Year's Day is detected"""
        dates = pd.date_range(start="2024-01-01", end="2024-01-02", freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "value": [1, 2]
        })

        generator = HolidayFeatureGenerator(country="US", state="NY")
        result = generator.generate(df)

        # January 1st should be a holiday
        assert result.loc[0, "is_holiday"] == 1


class TestFeatureIntegration:
    """Test full feature engineering pipeline"""

    def test_full_pipeline(self, sample_bike_data, sample_weather_data):
        """Test running all feature generators together"""
        df = sample_bike_data.copy()

        # Temporal
        temporal_gen = TemporalFeatureGenerator()
        df = temporal_gen.generate(df)

        # Lag
        lag_gen = LagFeatureGenerator(lag_hours=[1, 3])
        df = lag_gen.generate(df)

        # Rolling
        rolling_gen = RollingFeatureGenerator(windows=[3], statistics=["mean"])
        df = rolling_gen.generate(df)

        # Merge weather
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            sample_weather_data.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )

        # Weather
        weather_gen = WeatherFeatureGenerator()
        df = weather_gen.generate(df)

        # Holiday
        holiday_gen = HolidayFeatureGenerator()
        df = holiday_gen.generate(df)

        # Should have many more columns than original
        assert len(df.columns) > len(sample_bike_data.columns) + 20

        # Should have same number of rows
        assert len(df) == len(sample_bike_data)
