"""Commands for FHIR ingestion service."""

from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

from shared.domain.commands import Command


@dataclass
class StoreFHIRBundle(Command):
    """Command to store raw FHIR bundle in MinIO."""
    bundle_id: str
    bundle_data: Dict[str, Any]
    source_system: str
    received_at: datetime
    source_ip: str = ""