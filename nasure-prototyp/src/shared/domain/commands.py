"""Base command and event interfaces shared across services."""

from dataclasses import dataclass


@dataclass
class Command:
    """Base class for all commands."""
    pass

@dataclass
class Event:
    """Base class for all domain events."""
    pass

@dataclass
class PseudonymizePatient(Command):
    """ Command to pseudonymize a patient based on provided data."""
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str  # 'YYYY-MM-DD'
    canton: str

@dataclass
class GetPatientByAHV(Command):
    """ Command to get patient_id by AHV number."""
    ahv_number: str

@dataclass
class GetPatientDetails(Command):
    """ Command to get patient details by patient_id."""
    patient_id: str

    