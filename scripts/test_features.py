"""
Test Feature Engineering Pipeline
Tests all feature generation modules
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger
from src.features.temporal_features import TemporalFeatureGenerator
from src.features.lag_features import LagFeatureGenerator
from src.features.rolling_features import RollingFeatureGenerator
from src.features.weather_features import WeatherFeatureGenerator
from src.features.holiday_features import HolidayFeatureGenerator


def create_sample_bike_data(n_records: int = 1000) -> pd.DataFrame:
    """Create sample bike station data"""
    logger.info(f"Creating {n_records} sample bike records")

    dates = pd.date_range(start="2024-01-01", periods=n_records, freq="H")

    df = pd.DataFrame({
        "station_id": np.random.choice(["station_1", "station_2", "station_3"], n_records),
        "timestamp": dates,
        "bikes_available": np.random.randint(0, 30, n_records),
        "docks_available": np.random.randint(0, 20, n_records),
    })

    return df


def create_sample_weather_data(n_records: int = 100) -> pd.DataFrame:
    """Create sample weather data"""
    logger.info(f"Creating {n_records} sample weather records")

    dates = pd.date_range(start="2024-01-01", periods=n_records, freq="H")

    df = pd.DataFrame({
        "timestamp": dates,
        "temperature": np.random.uniform(-5, 30, n_records),
        "feels_like": np.random.uniform(-10, 28, n_records),
        "humidity": np.random.randint(30, 95, n_records),
        "wind_speed": np.random.uniform(0, 15, n_records),
        "precipitation": np.random.choice([0, 0, 0, 0.5, 2.0, 5.0], n_records),
        "weather_condition": np.random.choice(
            ["Clear", "Clouds", "Rain", "Snow"], n_records
        ),
        "visibility": np.random.randint(1000, 10000, n_records),
        "pressure": np.random.randint(980, 1040, n_records),
    })

    return df


def test_temporal_features():
    """Test temporal feature generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Temporal Features")
    logger.info("=" * 60)

    try:
        # Create sample data
        df = create_sample_bike_data(100)

        # Generate features
        logger.info("\n1. Generating temporal features...")
        generator = TemporalFeatureGenerator()
        df_with_features = generator.generate(df)

        # Verify features
        feature_names = generator.get_feature_names()
        logger.info(f"✓ Generated {len(feature_names)} features")
        logger.info(f"  Features: {', '.join(feature_names[:10])}...")

        # Check specific features
        assert "hour_of_day" in df_with_features.columns
        assert "is_weekend" in df_with_features.columns
        assert "season" in df_with_features.columns
        assert "is_rush_hour" in df_with_features.columns
        assert "hour_sin" in df_with_features.columns

        logger.info("\n2. Sample feature values:")
        logger.info(f"  Hour range: {df_with_features['hour_of_day'].min()}-{df_with_features['hour_of_day'].max()}")
        logger.info(f"  Weekends: {df_with_features['is_weekend'].sum()} records")
        logger.info(f"  Rush hours: {df_with_features['is_rush_hour'].sum()} records")
        logger.info(f"  Seasons: {df_with_features['season'].value_counts().to_dict()}")

        logger.info("\n✅ Temporal features test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Temporal features test FAILED: {e}")
        return False


def test_lag_features():
    """Test lag feature generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Lag Features")
    logger.info("=" * 60)

    try:
        # Create sample data
        df = create_sample_bike_data(200)

        # Generate features
        logger.info("\n1. Generating lag features...")
        generator = LagFeatureGenerator(
            lag_hours=[1, 3, 6, 24],
            target_column="bikes_available"
        )
        df_with_features = generator.generate(df)

        # Verify features
        feature_names = generator.get_feature_names()
        logger.info(f"✓ Generated {len(feature_names)} features")
        logger.info(f"  Features: {', '.join(feature_names)}")

        # Check specific features
        assert "bikes_available_lag_1h" in df_with_features.columns
        assert "bikes_available_lag_24h" in df_with_features.columns
        assert "bikes_available_change_1h" in df_with_features.columns
        assert "bikes_available_pct_change_1h" in df_with_features.columns

        logger.info("\n2. Sample lag values:")
        logger.info(f"  Lag 1h non-null: {df_with_features['bikes_available_lag_1h'].notna().sum()} / {len(df_with_features)}")
        logger.info(f"  Lag 24h non-null: {df_with_features['bikes_available_lag_24h'].notna().sum()} / {len(df_with_features)}")

        logger.info("\n✅ Lag features test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Lag features test FAILED: {e}")
        return False


def test_rolling_features():
    """Test rolling window feature generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Rolling Features")
    logger.info("=" * 60)

    try:
        # Create sample data
        df = create_sample_bike_data(200)

        # Generate features
        logger.info("\n1. Generating rolling features...")
        generator = RollingFeatureGenerator(
            windows=[3, 6, 12],
            statistics=["mean", "std", "min", "max"],
            target_column="bikes_available"
        )
        df_with_features = generator.generate(df)

        # Verify features
        feature_names = generator.get_feature_names()
        logger.info(f"✓ Generated {len(feature_names)} features")
        logger.info(f"  Sample features: {', '.join(feature_names[:6])}...")

        # Check specific features
        assert "bikes_available_rolling_mean_3h" in df_with_features.columns
        assert "bikes_available_rolling_std_12h" in df_with_features.columns
        assert "bikes_available_rolling_max_6h" in df_with_features.columns

        logger.info("\n2. Sample rolling values:")
        mean_3h = df_with_features["bikes_available_rolling_mean_3h"]
        logger.info(f"  3h mean range: {mean_3h.min():.2f} - {mean_3h.max():.2f}")

        logger.info("\n✅ Rolling features test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Rolling features test FAILED: {e}")
        return False


def test_weather_features():
    """Test weather feature generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Weather Features")
    logger.info("=" * 60)

    try:
        # Create sample data
        df = create_sample_weather_data(100)

        # Generate features
        logger.info("\n1. Generating weather features...")
        generator = WeatherFeatureGenerator()
        df_with_features = generator.generate(df)

        # Verify features
        feature_names = generator.get_feature_names()
        logger.info(f"✓ Generated {len(feature_names)} features")
        logger.info(f"  Sample features: {', '.join(feature_names[:10])}...")

        # Check specific features
        assert "temperature_normalized" in df_with_features.columns
        assert "is_rainy" in df_with_features.columns
        assert "wind_category" in df_with_features.columns
        assert "weather_severity" in df_with_features.columns

        logger.info("\n2. Sample weather feature values:")
        logger.info(f"  Rainy records: {df_with_features['is_rainy'].sum()} / {len(df_with_features)}")
        logger.info(f"  Wind categories: {df_with_features['wind_category'].value_counts().to_dict()}")
        logger.info(f"  Weather severity: {df_with_features['weather_severity'].value_counts().to_dict()}")

        logger.info("\n✅ Weather features test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Weather features test FAILED: {e}")
        return False


def test_holiday_features():
    """Test holiday feature generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Holiday Features")
    logger.info("=" * 60)

    try:
        # Create sample data spanning a year
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "value": np.random.randn(len(dates))
        })

        # Generate features
        logger.info("\n1. Generating holiday features...")
        generator = HolidayFeatureGenerator(country="US", state="NY")
        df_with_features = generator.generate(df)

        # Verify features
        feature_names = generator.get_feature_names()
        logger.info(f"✓ Generated {len(feature_names)} features")
        logger.info(f"  Features: {', '.join(feature_names)}")

        # Check specific features
        assert "is_holiday" in df_with_features.columns
        assert "is_holiday_eve" in df_with_features.columns
        assert "days_to_next_holiday" in df_with_features.columns
        assert "is_major_holiday" in df_with_features.columns

        logger.info("\n2. Sample holiday feature values:")
        logger.info(f"  Total holidays: {df_with_features['is_holiday'].sum()} days")
        logger.info(f"  Major holidays: {df_with_features['is_major_holiday'].sum()} days")

        # Show some holidays
        holidays_df = df_with_features[df_with_features['is_holiday'] == 1]
        if len(holidays_df) > 0:
            logger.info(f"\n3. Sample holidays found:")
            for _, row in holidays_df.head(5).iterrows():
                logger.info(f"  - {row['timestamp'].strftime('%Y-%m-%d')}: {row['holiday_name']}")

        logger.info("\n✅ Holiday features test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Holiday features test FAILED: {e}")
        return False


def test_full_pipeline():
    """Test complete feature engineering pipeline"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Full Feature Engineering Pipeline")
    logger.info("=" * 60)

    try:
        # Create sample data
        bike_df = create_sample_bike_data(500)
        weather_df = create_sample_weather_data(500)

        logger.info("\n1. Starting with bike data...")
        logger.info(f"  Initial columns: {list(bike_df.columns)}")
        logger.info(f"  Records: {len(bike_df)}")

        # Generate all features
        logger.info("\n2. Generating all feature types...")

        # Temporal
        temporal_gen = TemporalFeatureGenerator()
        df = temporal_gen.generate(bike_df)
        logger.info(f"  + {len(temporal_gen.get_feature_names())} temporal features")

        # Lag
        lag_gen = LagFeatureGenerator(lag_hours=[1, 3, 6, 24])
        df = lag_gen.generate(df)
        logger.info(f"  + {len(lag_gen.get_feature_names())} lag features")

        # Rolling
        rolling_gen = RollingFeatureGenerator(windows=[3, 6, 12], statistics=["mean", "std"])
        df = rolling_gen.generate(df)
        logger.info(f"  + {len(rolling_gen.get_feature_names())} rolling features")

        # Merge weather
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            weather_df.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )

        # Weather
        weather_gen = WeatherFeatureGenerator()
        df = weather_gen.generate(df)
        logger.info(f"  + {len(weather_gen.get_feature_names())} weather features")

        # Holiday
        holiday_gen = HolidayFeatureGenerator()
        df = holiday_gen.generate(df)
        logger.info(f"  + {len(holiday_gen.get_feature_names())} holiday features")

        # Summary
        total_features = (
            len(temporal_gen.get_feature_names()) +
            len(lag_gen.get_feature_names()) +
            len(rolling_gen.get_feature_names()) +
            len(weather_gen.get_feature_names()) +
            len(holiday_gen.get_feature_names())
        )

        logger.info(f"\n3. Pipeline summary:")
        logger.info(f"  Total features generated: {total_features}")
        logger.info(f"  Final columns: {len(df.columns)}")
        logger.info(f"  Final records: {len(df)}")

        logger.info("\n✅ Full pipeline test PASSED")
        return True

    except Exception as e:
        logger.error(f"\n❌ Full pipeline test FAILED: {e}")
        return False


def main():
    """Run all feature engineering tests"""
    logger.info("\n" + "=" * 60)
    logger.info("FEATURE ENGINEERING PIPELINE TEST")
    logger.info("=" * 60)

    results = {
        "Temporal Features": test_temporal_features(),
        "Lag Features": test_lag_features(),
        "Rolling Features": test_rolling_features(),
        "Weather Features": test_weather_features(),
        "Holiday Features": test_holiday_features(),
        "Full Pipeline": test_full_pipeline(),
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
        logger.info("\n🎉 All feature engineering tests passed!")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
