"""
Data Validator
Validates collected data using Great Expectations
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
from loguru import logger


class DataValidator:
    """Validator for bike demand data quality"""

    def __init__(self):
        """Initialize data validator"""
        self.validation_results = []

    def validate_station_information(self, stations_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate station information data

        Args:
            stations_df: DataFrame with station information

        Returns:
            Validation results dictionary
        """
        logger.info("Validating station information data")

        results = {
            "data_type": "station_information",
            "timestamp": datetime.utcnow().isoformat(),
            "total_records": len(stations_df),
            "checks": [],
            "passed": True,
        }

        # Check 1: Required columns exist
        required_columns = ["station_id", "name", "latitude", "longitude", "capacity"]
        missing_columns = [col for col in required_columns if col not in stations_df.columns]

        if missing_columns:
            results["checks"].append({
                "check": "required_columns",
                "status": "failed",
                "message": f"Missing columns: {missing_columns}"
            })
            results["passed"] = False
        else:
            results["checks"].append({
                "check": "required_columns",
                "status": "passed"
            })

        # Check 2: No null values in required columns
        null_counts = stations_df[required_columns].isnull().sum()
        if null_counts.any():
            results["checks"].append({
                "check": "null_values",
                "status": "failed",
                "message": f"Null values found: {null_counts[null_counts > 0].to_dict()}"
            })
            results["passed"] = False
        else:
            results["checks"].append({
                "check": "null_values",
                "status": "passed"
            })

        # Check 3: Latitude range (-90 to 90)
        if "latitude" in stations_df.columns:
            invalid_lat = stations_df[(stations_df["latitude"] < -90) | (stations_df["latitude"] > 90)]
            if len(invalid_lat) > 0:
                results["checks"].append({
                    "check": "latitude_range",
                    "status": "failed",
                    "message": f"{len(invalid_lat)} records with invalid latitude"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "latitude_range",
                    "status": "passed"
                })

        # Check 4: Longitude range (-180 to 180)
        if "longitude" in stations_df.columns:
            invalid_lon = stations_df[(stations_df["longitude"] < -180) | (stations_df["longitude"] > 180)]
            if len(invalid_lon) > 0:
                results["checks"].append({
                    "check": "longitude_range",
                    "status": "failed",
                    "message": f"{len(invalid_lon)} records with invalid longitude"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "longitude_range",
                    "status": "passed"
                })

        # Check 5: Capacity is positive
        if "capacity" in stations_df.columns:
            invalid_capacity = stations_df[stations_df["capacity"] <= 0]
            if len(invalid_capacity) > 0:
                results["checks"].append({
                    "check": "capacity_positive",
                    "status": "failed",
                    "message": f"{len(invalid_capacity)} records with invalid capacity"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "capacity_positive",
                    "status": "passed"
                })

        # Check 6: Unique station IDs
        if "station_id" in stations_df.columns:
            duplicates = stations_df[stations_df["station_id"].duplicated()]
            if len(duplicates) > 0:
                results["checks"].append({
                    "check": "unique_station_ids",
                    "status": "failed",
                    "message": f"{len(duplicates)} duplicate station IDs found"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "unique_station_ids",
                    "status": "passed"
                })

        logger.info(f"Station information validation: {'PASSED' if results['passed'] else 'FAILED'}")
        self.validation_results.append(results)

        return results

    def validate_station_status(self, status_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate station status data

        Args:
            status_df: DataFrame with station status

        Returns:
            Validation results dictionary
        """
        logger.info("Validating station status data")

        results = {
            "data_type": "station_status",
            "timestamp": datetime.utcnow().isoformat(),
            "total_records": len(status_df),
            "checks": [],
            "passed": True,
        }

        # Check 1: Required columns exist
        required_columns = ["station_id", "timestamp", "bikes_available", "docks_available"]
        missing_columns = [col for col in required_columns if col not in status_df.columns]

        if missing_columns:
            results["checks"].append({
                "check": "required_columns",
                "status": "failed",
                "message": f"Missing columns: {missing_columns}"
            })
            results["passed"] = False
        else:
            results["checks"].append({
                "check": "required_columns",
                "status": "passed"
            })

        # Check 2: No negative values for bikes/docks
        if "bikes_available" in status_df.columns:
            negative_bikes = status_df[status_df["bikes_available"] < 0]
            if len(negative_bikes) > 0:
                results["checks"].append({
                    "check": "bikes_non_negative",
                    "status": "failed",
                    "message": f"{len(negative_bikes)} records with negative bikes"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "bikes_non_negative",
                    "status": "passed"
                })

        if "docks_available" in status_df.columns:
            negative_docks = status_df[status_df["docks_available"] < 0]
            if len(negative_docks) > 0:
                results["checks"].append({
                    "check": "docks_non_negative",
                    "status": "failed",
                    "message": f"{len(negative_docks)} records with negative docks"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "docks_non_negative",
                    "status": "passed"
                })

        # Check 3: Timestamps are reasonable (within last hour to future 5 minutes)
        if "timestamp" in status_df.columns:
            now = pd.Timestamp.utcnow()
            one_hour_ago = now - pd.Timedelta(hours=1)
            five_min_future = now + pd.Timedelta(minutes=5)

            invalid_timestamps = status_df[
                (pd.to_datetime(status_df["timestamp"]) < one_hour_ago) |
                (pd.to_datetime(status_df["timestamp"]) > five_min_future)
            ]

            if len(invalid_timestamps) > 0:
                results["checks"].append({
                    "check": "timestamp_range",
                    "status": "warning",
                    "message": f"{len(invalid_timestamps)} records with unusual timestamps"
                })
            else:
                results["checks"].append({
                    "check": "timestamp_range",
                    "status": "passed"
                })

        # Check 4: No null station_ids
        if "station_id" in status_df.columns:
            null_station_ids = status_df[status_df["station_id"].isnull()]
            if len(null_station_ids) > 0:
                results["checks"].append({
                    "check": "station_id_not_null",
                    "status": "failed",
                    "message": f"{len(null_station_ids)} records with null station_id"
                })
                results["passed"] = False
            else:
                results["checks"].append({
                    "check": "station_id_not_null",
                    "status": "passed"
                })

        logger.info(f"Station status validation: {'PASSED' if results['passed'] else 'FAILED'}")
        self.validation_results.append(results)

        return results

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of all validation results

        Returns:
            Summary dictionary
        """
        if not self.validation_results:
            return {
                "total_validations": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            }

        total = len(self.validation_results)
        passed = sum(1 for r in self.validation_results if r["passed"])
        failed = total - passed

        # Count warnings
        warnings = 0
        for result in self.validation_results:
            warnings += sum(1 for check in result["checks"] if check["status"] == "warning")

        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "results": self.validation_results,
        }


# Singleton instance
data_validator = DataValidator()
