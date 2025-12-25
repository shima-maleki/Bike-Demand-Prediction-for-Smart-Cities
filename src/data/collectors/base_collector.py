"""
Base Collector Abstract Class
Provides common functionality for all data collectors
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
import requests
from datetime import datetime
from loguru import logger


class BaseCollector(ABC):
    """Abstract base class for data collectors"""

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize base collector

        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.last_request_time: Optional[datetime] = None

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        Collect data from the source

        Returns:
            Dict containing collected data
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate collected data

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API

        Args:
            endpoint: API endpoint
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            headers: Request headers

        Returns:
            Response data as dictionary

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith("http") else endpoint

        try:
            logger.debug(f"Making {method} request to {url}")
            self.last_request_time = datetime.now()

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Successfully received data from {url}")
            return data

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response from {url}: {e}")
            raise

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the collector

        Returns:
            Dictionary with collector metadata
        """
        return {
            "collector_type": self.__class__.__name__,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
        }

    def close(self) -> None:
        """Close the session"""
        if self.session:
            self.session.close()
            logger.debug("Collector session closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
