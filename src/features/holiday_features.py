"""
Holiday Feature Engineering
Generates holiday-based features for bike demand forecasting
"""

import pandas as pd
from typing import List
from datetime import timedelta
from loguru import logger
import holidays

from src.features.base_features import BaseFeatureGenerator


class HolidayFeatureGenerator(BaseFeatureGenerator):
    """Generator for holiday-based features"""

    def __init__(
        self,
        timestamp_column: str = "timestamp",
        country: str = "US",
        state: str = "NY",
        feature_version: str = "v1.0"
    ):
        """
        Initialize holiday feature generator

        Args:
            timestamp_column: Name of timestamp column
            country: Country code for holidays
            state: State/province code for holidays
            feature_version: Version identifier
        """
        super().__init__(feature_version)
        self.timestamp_column = timestamp_column
        self.country = country
        self.state = state

        # Initialize holidays for the country/state
        try:
            self.holiday_calendar = holidays.country_holidays(country, subdiv=state)
        except Exception as e:
            logger.warning(f"Failed to load holidays for {country}/{state}: {e}")
            self.holiday_calendar = holidays.country_holidays(country)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate holiday features

        Args:
            df: Input DataFrame with timestamp column

        Returns:
            DataFrame with holiday features added
        """
        logger.info(f"Generating holiday features for {self.country}/{self.state}")

        # Validate input
        if not self.validate_input(df, [self.timestamp_column]):
            raise ValueError(f"Missing required column: {self.timestamp_column}")

        original_cols = len(df.columns)
        df = df.copy()

        # Ensure timestamp is datetime
        df[self.timestamp_column] = pd.to_datetime(df[self.timestamp_column])
        df["date"] = df[self.timestamp_column].dt.date

        # Is holiday
        df["is_holiday"] = df["date"].apply(lambda x: x in self.holiday_calendar).astype(int)
        self.feature_names.append("is_holiday")

        # Holiday name
        df["holiday_name"] = df["date"].apply(
            lambda x: self.holiday_calendar.get(x, None)
        )
        self.feature_names.append("holiday_name")

        # Is holiday eve (day before holiday)
        df["is_holiday_eve"] = df["date"].apply(
            lambda x: (x + timedelta(days=1)) in self.holiday_calendar
        ).astype(int)
        self.feature_names.append("is_holiday_eve")

        # Is holiday after (day after holiday)
        df["is_holiday_after"] = df["date"].apply(
            lambda x: (x - timedelta(days=1)) in self.holiday_calendar
        ).astype(int)
        self.feature_names.append("is_holiday_after")

        # Days to next holiday
        df["days_to_next_holiday"] = df["date"].apply(self._days_to_next_holiday)
        self.feature_names.append("days_to_next_holiday")

        # Days from last holiday
        df["days_from_last_holiday"] = df["date"].apply(self._days_from_last_holiday)
        self.feature_names.append("days_from_last_holiday")

        # Is holiday week (within 3 days of a holiday)
        df["is_holiday_week"] = (
            (df["days_to_next_holiday"] <= 3) | (df["days_from_last_holiday"] <= 3)
        ).astype(int)
        self.feature_names.append("is_holiday_week")

        # Major holidays (Thanksgiving, Christmas, New Year, etc.)
        if "holiday_name" in df.columns:
            major_holidays = [
                "New Year's Day",
                "Independence Day",
                "Thanksgiving",
                "Christmas Day",
                "Memorial Day",
                "Labor Day"
            ]
            df["is_major_holiday"] = df["holiday_name"].apply(
                lambda x: 1 if x in major_holidays else 0
            )
            self.feature_names.append("is_major_holiday")

        # Drop temporary date column
        df = df.drop(columns=["date"])

        self.log_generation_summary(df, original_cols)

        return df

    def _days_to_next_holiday(self, date) -> int:
        """
        Calculate days to next holiday

        Args:
            date: Date to check

        Returns:
            Number of days to next holiday
        """
        days = 0
        check_date = date
        max_days = 365  # Look ahead maximum 1 year

        while days < max_days:
            check_date = check_date + timedelta(days=1)
            if check_date in self.holiday_calendar:
                return days + 1
            days += 1

        return max_days  # Return max if no holiday found

    def _days_from_last_holiday(self, date) -> int:
        """
        Calculate days from last holiday

        Args:
            date: Date to check

        Returns:
            Number of days from last holiday
        """
        days = 0
        check_date = date
        max_days = 365  # Look back maximum 1 year

        while days < max_days:
            check_date = check_date - timedelta(days=1)
            if check_date in self.holiday_calendar:
                return days + 1
            days += 1

        return max_days  # Return max if no holiday found

    def get_feature_names(self) -> List[str]:
        """Get list of generated feature names"""
        return self.feature_names


# Convenience function
def generate_holiday_features(
    df: pd.DataFrame,
    timestamp_column: str = "timestamp",
    country: str = "US",
    state: str = "NY"
) -> pd.DataFrame:
    """
    Generate holiday features from DataFrame

    Args:
        df: Input DataFrame
        timestamp_column: Name of timestamp column
        country: Country code for holidays
        state: State/province code for holidays

    Returns:
        DataFrame with holiday features
    """
    generator = HolidayFeatureGenerator(
        timestamp_column=timestamp_column,
        country=country,
        state=state
    )
    return generator.generate(df)
