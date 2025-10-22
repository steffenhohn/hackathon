"""
Minimal Laboratory Surveillance Domain Model
Based on CH-eLM FHIR documents - Essential data only
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class ResultInterpretation(Enum):
    """Standard result interpretations for surveillance"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class TestCode:
    """Minimal test identification - surveillance focused"""
    loinc_code: str                    # e.g., "697-3"
    loinc_display: str                 # e.g., "Neisseria gonorrhoeae [Presence]..."
    pathogen: str                      # e.g., "neisseria_gonorrhoeae"


@dataclass(frozen=True)
class TestResult:
    """Minimal test result - surveillance focused"""
    interpretation: ResultInterpretation
    snomed_code: Optional[str] = None          # e.g., "10828004"
    snomed_display: Optional[str] = None       # e.g., "Positive"


@dataclass(frozen=True)
class Specimen:
    """Minimal specimen info - surveillance relevant only"""
    collection_date: Optional[datetime] = None
    specimen_type: Optional[str] = None         # Derived from observation context


@dataclass
class LaboratoryObservation:
    """Core surveillance observation from FHIR Observation"""
    observation_id: str                         # From FHIR Observation.id
    test_code: TestCode
    result: TestResult
    test_date: Optional[datetime] = None        # From effectiveDateTime
    specimen: Optional[Specimen] = None

    def is_positive(self) -> bool:
        """Check if result is positive"""
        return self.result.interpretation == ResultInterpretation.POSITIVE


@dataclass
class LaboratoryReport:
    """
    Minimal Laboratory Surveillance Report
    Maps directly to CH-eLM FHIR Bundle structure
    """
    # Core identification (from FHIR Bundle)
    report_id: UUID = field(default_factory=uuid4)
    bundle_id: str = ""                         # From Bundle.id
    fhir_identifier: str = ""                   # From Bundle.identifier.value

    # Timing (from FHIR Bundle and Composition)
    report_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    composition_date: Optional[datetime] = None  # From Composition.date
    ingestion_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Clean entity references (mapped from FHIR references)
    patient_id: str = ""                        # Clean patient identifier
    pathogen: str = ""                          # Primary pathogen (e.g., "neisseria_gonorrhoeae")
    performing_lab_id: str = ""                 # From Organization GLN (e.g., "7601002331470")
    ordering_facility_id: Optional[str] = None  # From requester Organization GLN

    # Core surveillance data
    observations: List[LaboratoryObservation] = field(default_factory=list)

    # Metadata
    report_status: str = "final"                # From Composition.status
    source_system: str = "ch-elm"

    def add_observation(self, observation: LaboratoryObservation):
        """Add observation to report"""
        self.observations.append(observation)

    def get_positive_results(self) -> List[LaboratoryObservation]:
        """Get all positive observations"""
        return [obs for obs in self.observations if obs.is_positive()]

    def get_results_for_pathogen(self, pathogen: str) -> List[LaboratoryObservation]:
        """Get observations for specific pathogen"""
        return [obs for obs in self.observations
                if obs.test_code.pathogen == pathogen]

    def has_positive_for_pathogen(self, pathogen: str) -> bool:
        """Check if report has positive result for pathogen"""
        return any(obs.is_positive() and obs.test_code.pathogen == pathogen
                  for obs in self.observations)

    def calculate_data_freshness_hours(self) -> float:
        """Calculate data freshness from most recent test"""
        if not self.observations:
            return 0.0

        test_dates = [obs.test_date for obs in self.observations if obs.test_date]
        if not test_dates:
            return 0.0

        most_recent = max(test_dates)
        now = datetime.now(timezone.utc)

        if most_recent.tzinfo is None:
            most_recent = most_recent.replace(tzinfo=timezone.utc)

        return (now - most_recent).total_seconds() / 3600

    def get_surveillance_summary(self) -> Dict[str, Any]:
        """Get clean surveillance data summary"""
        positive_results = self.get_positive_results()

        # Count by pathogen
        pathogen_counts = {}
        for obs in positive_results:
            pathogen = obs.test_code.pathogen
            pathogen_counts[pathogen] = pathogen_counts.get(pathogen, 0) + 1

        return {
            "report_id": str(self.report_id),
            "bundle_id": self.bundle_id,
            "fhir_identifier": self.fhir_identifier,
            "report_timestamp": self.report_timestamp.isoformat(),
            "patient_id": self.patient_id,
            "pathogen": self.pathogen,
            "performing_lab_id": self.performing_lab_id,
            "ordering_facility_id": self.ordering_facility_id,
            "total_observations": len(self.observations),
            "positive_results": len(positive_results),
            "pathogen_summary": pathogen_counts,
            "data_freshness_hours": self.calculate_data_freshness_hours(),
            "source_system": self.source_system
        }


# CH-eLM specific pathogen mappings (minimal set)
CH_ELM_PATHOGEN_MAPPINGS = {
    "697-3": "neisseria_gonorrhoeae",
    "21415-5": "neisseria_gonorrhoeae",
    "21613-5": "chlamydia_trachomatis",
    "6349-5": "chlamydia_trachomatis",
    "5292-8": "treponema_pallidum",
    "20507-0": "treponema_pallidum"
}

# SNOMED result interpretation mappings
SNOMED_RESULT_MAPPINGS = {
    "10828004": ResultInterpretation.POSITIVE,    # Positive
    "260385009": ResultInterpretation.NEGATIVE,   # Negative
    "419984006": ResultInterpretation.INCONCLUSIVE  # Inconclusive
}