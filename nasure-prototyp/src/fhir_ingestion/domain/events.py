"""Domain events for FHIR ingestion service."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

from shared.domain.commands import Event


@dataclass
class BundleStored(Event):
    """Event raised when a FHIR bundle has been successfully stored in MinIO."""
    bundle_id: str
    object_key: str
    source_system: str
    stored_at: datetime
    bundle_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

