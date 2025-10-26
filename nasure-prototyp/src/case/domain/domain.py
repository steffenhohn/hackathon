from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class CaseRecord:
    """Domain model for a Case record."""
    case_id: str              # UUID4 as String
    patient_id: str           # normalised (numbers only)
    pathogen_code: str        # Pathogen LOINC code    
    pathogen_description: str # Pathogen description
    lab_timestamp: datetime   # lab report timestamp
    created_at: datetime      # when the case was created at
    case_class: str           # Case classification: sicherer Fall, wahrscheinlicher Fall, Verdachtsfall
    status: str               # Case status: neu, in Bearbeitung, abgeschlossen, archiviert
    canton: str               # 2 letter canton code

    def __hash__(self):
        """Make object hashable based on case_id."""
        return hash(self.case_id)
    
    def __eq__(self, other):
        """Equality based on case_id."""
        if not isinstance(other, CaseRecord):
            return False
        return self.case_id == other.case_id

@dataclass
class CaseToProductRecord:
    """Domain model for linking Cases to Data Products."""
    case_id: str              # FK to case
    product_id: str           # FK to product
