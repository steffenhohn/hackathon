"""
Views for read operations - separate from command/write path.
Following Cosmic Python pattern: views bypass the domain model for reads.
"""
import logging
from typing import Optional, Dict, Any

from fhir_ingestion.service_layer.unit_of_work import FHIRIngestionUnitOfWork

logger = logging.getLogger(__name__)


def get_bundle(bundle_id: str, uow: FHIRIngestionUnitOfWork) -> Optional[Dict[str, Any]]:
    """
    Retrieve FHIR bundle by bundle_id.

    This is a read-only view that bypasses the domain model.
    """
    with uow:
        bundle_data = uow.bundles.get_by_bundle_id(bundle_id)

    return bundle_data