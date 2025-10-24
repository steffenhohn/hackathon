"""FHIR Ingestion API Client - Adapter for fetching stored FHIR bundles."""

import abc
import logging
from typing import Dict, Any, Optional
import requests

import config

logger = logging.getLogger(__name__)


class AbstractFHIRClient(abc.ABC):
    """Abstract base class for FHIR client implementations."""

    @abc.abstractmethod
    def get_bundle(self, bundle_id: str) -> Dict[str, Any]:
        """
        Fetch a FHIR bundle by bundle_id.

        Args:
            bundle_id: The unique identifier for the bundle

        Returns:
            Dict containing the FHIR bundle data

        Raises:
            FHIRClientError: If the request fails or bundle not found
        """
        raise NotImplementedError


class HTTPFHIRClient(AbstractFHIRClient):
    """HTTP-based client to interact with FHIR Ingestion service API."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize FHIR client.

        Args:
            base_url: Base URL for FHIR Ingestion API. If None, uses config.
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.get_api_url()
        self.timeout = timeout

    def get_bundle(self, bundle_id: str) -> Dict[str, Any]:
        """
        Fetch a FHIR bundle by bundle_id from the ingestion service.

        Args:
            bundle_id: The unique identifier for the bundle

        Returns:
            Dict containing the FHIR bundle data

        Raises:
            FHIRClientError: If the request fails or bundle not found
        """
        url = f"{self.base_url}/api/v1/fhir/bundle/{bundle_id}"

        logger.info(f"Fetching bundle {bundle_id} from {url}")

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            bundle_data = response.json()
            logger.info(f"Successfully fetched bundle {bundle_id}")
            return bundle_data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Bundle {bundle_id} not found")
                raise FHIRClientError(f"Bundle {bundle_id} not found") from e
            else:
                logger.error(f"HTTP error fetching bundle {bundle_id}: {e}")
                raise FHIRClientError(f"Failed to fetch bundle: {e}") from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching bundle {bundle_id}: {e}")
            raise FHIRClientError(f"Network error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error fetching bundle {bundle_id}: {e}")
            raise FHIRClientError(f"Unexpected error: {e}") from e


class FHIRClientError(Exception):
    """Exception raised for errors in the FHIR client."""
    pass
