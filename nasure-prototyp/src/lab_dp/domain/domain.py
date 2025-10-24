from dataclasses import dataclass, field
from typing import List


@dataclass(unsafe_hash=True)
class LabDataProduct:
    product_id: str
    patient_id: str
    bundle_id: str
    timestamp: str
    pathogen_code: str
    pathogen_description: str
    interpretation: str
    version_number: int = 0
    events: List = field(default_factory=list, compare=False, hash=False)
