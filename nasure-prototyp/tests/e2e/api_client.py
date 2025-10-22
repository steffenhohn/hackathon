"""API client for e2e tests following Cosmic Python pattern"""
import requests
from typing import Dict, Any

from config import get_api_url


def post_to_fhir_ingest(bundle: Dict[str, Any], source_system: str = "ch-elm"):
    """Post FHIR bundle to ingestion API

    Sends the bundle directly as per FHIR REST API standard.
    The source_system is sent as a query parameter.
    """
    url = f"{get_api_url()}/api/v1/fhir/ingest"
    response = requests.post(
        url,
        json=bundle,
        params={"source_system": source_system}
    )
    return response


def get_health():
    """Get health check from API"""
    url = f"{get_api_url()}/health"
    return requests.get(url)