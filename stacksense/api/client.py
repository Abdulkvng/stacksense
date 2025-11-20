"""
API client for communicating with StackSense backend
"""

import requests
from typing import Dict, Any, List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from stacksense.logger.logger import get_logger


class APIClient:
    """
    Client for StackSense API communication.
    """

    def __init__(self, settings):
        """
        Initialize API client.

        Args:
            settings: StackSense settings object
        """
        self.settings = settings
        self.logger = get_logger(__name__, debug=settings.debug)
        self.base_url = settings.api_base_url

        # Setup session with retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=self.settings.max_retries,
            backoff_factor=self.settings.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json", "User-Agent": "StackSense-Python/0.1.0"}

        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        return headers

    def send_events(self, events: List[Dict[str, Any]]) -> bool:
        """
        Send events to the API.

        Args:
            events: List of event dictionaries

        Returns:
            True if successful, False otherwise
        """
        if not events:
            return True

        try:
            url = f"{self.base_url}/events"
            payload = {
                "project_id": self.settings.project_id,
                "environment": self.settings.environment,
                "events": events,
            }

            response = self.session.post(url, json=payload, headers=self._get_headers(), timeout=10)

            response.raise_for_status()

            self.logger.debug(f"Sent {len(events)} events to API")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send events: {e}")
            return False

    def get_metrics(self, timeframe: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch metrics from the API.

        Args:
            timeframe: Time period filter

        Returns:
            Metrics dictionary or None if failed
        """
        try:
            url = f"{self.base_url}/metrics"
            params = {
                "project_id": self.settings.project_id,
            }

            if timeframe:
                params["timeframe"] = timeframe

            response = self.session.get(url, params=params, headers=self._get_headers(), timeout=10)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch metrics: {e}")
            return None

    def create_project(self, name: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Create a new project.

        Args:
            name: Project name
            metadata: Additional project metadata

        Returns:
            Project ID or None if failed
        """
        try:
            url = f"{self.base_url}/projects"
            payload = {"name": name, "metadata": metadata or {}}

            response = self.session.post(url, json=payload, headers=self._get_headers(), timeout=10)

            response.raise_for_status()
            data = response.json()

            return data.get("project_id")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create project: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check API health.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
