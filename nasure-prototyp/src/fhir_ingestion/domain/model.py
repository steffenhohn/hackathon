"""Domain model for FHIR bundle storage."""

from datetime import datetime, timezone
from typing import Dict, Any, List

from fhir_ingestion.domain.events import BundleStored


class FhirBundle:
    """Domain entity representing a FHIR bundle in storage."""

    def __init__(self, bundle_id: str, bundle_data: Dict[str, Any], bundle_type: str, source_system: str):
        self.bundle_id = bundle_id
        self.bundle_data = bundle_data
        self.bundle_type = bundle_type
        self.source_system = source_system
        self.stored_at = None
        self.object_key = None
        self.events: List = []

    def store(self, object_key: str) -> str:
        """
        Mark bundle as stored and generate domain events.

        This is where events are generated in the domain, not in handlers.
        """
        self.object_key = object_key
        self.stored_at = datetime.now(timezone.utc)

        # Generate domain event - simple BundleStored event
        self.events.append(
            BundleStored(
                bundle_id=self.bundle_id,
                object_key=self.object_key,
                bundle_type=self.bundle_type,
                source_system=self.source_system,
                stored_at=self.stored_at
            )
        )

        return object_key