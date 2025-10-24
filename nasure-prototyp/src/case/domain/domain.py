from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CaseRecord:
    case_id: str              # UUID4 as String
    patient_id: str           # normalised (numbers only)
    case_date: str            # 'YYYY-MM-DD'
    case_class: str
    case_status: str          
    pathogen: str            
    canton: str               # 2 letter canton code

@dataclass
class CaseToProductRecord:
    case_id: str              # FK to case
    product_id: str           # FK to product
