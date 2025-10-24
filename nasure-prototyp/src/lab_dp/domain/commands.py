"""Commands for lab data product service."""

from dataclasses import dataclass
from datetime import datetime

from shared.domain.commands import Command


@dataclass
class CreateDataProduct(Command):
    """Command to generate surveillance data product from stored FHIR bundle."""
    bundle_id: str
    stored_at: datetime  # When the bundle was stored by fhir_ingestion
