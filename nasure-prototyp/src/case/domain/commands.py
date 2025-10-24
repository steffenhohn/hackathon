"""Commands for case mgmt service."""

from dataclasses import dataclass
from datetime import datetime

from shared.domain.commands import Command


@dataclass
class CreateCaseFromDataProduct(Command):
    """Comand to create a new case in case management."""
    product_id: str
    patient_id: str
    pathogen_code: str
    pathogen_description: str
    timestamp: str  # Lab report timestamp (from FHIR bundle)
    stored_at: datetime  # When the bundle was stored by fhir_ingestion (BundleStored event)
    created_at: datetime  # When the data product was created
