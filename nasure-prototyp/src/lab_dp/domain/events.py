"""Domain events for lab data product service."""

from dataclasses import dataclass
from datetime import datetime

from shared.domain.commands import Event


@dataclass
class DataProductCreated(Event):
    """Event raised when a lab data product has been successfully created."""
    product_id: str
    pathogen_code: str
    pathogen_description: str
    timestamp: str  # Lab report timestamp (from FHIR bundle)
    stored_at: datetime  # When the bundle was stored by fhir_ingestion (BundleStored event)
    created_at: datetime  # When the data product was created
