"""Simple pseudonymization functions that return unique UUIDs."""

import uuid
from typing import Dict, Any, Tuple


def pseudonymize_patient(patient_resource: Dict[str, Any]) -> Tuple[str, str]:
    """
    Pseudonymize FHIR Patient resource.

    Args:
        patient_resource: FHIR Patient resource (not used for now)

    Returns:
        Tuple of (unique_uuid, method_used)
    """
    return str(uuid.uuid4()), "uuid"


def pseudonymize_organization(organization_resource: Dict[str, Any]) -> Tuple[str, str]:
    """
    Pseudonymize FHIR Organization resource.

    Args:
        organization_resource: FHIR Organization resource (not used for now)

    Returns:
        Tuple of (unique_uuid, method_used)
    """
    return str(uuid.uuid4()), "uuid"