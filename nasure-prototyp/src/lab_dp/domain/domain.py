from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timezone

from lab_dp.domain.events import DataProductCreated


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

    def create(self) -> None:
        """
        Mark product as created and generate domain event.

        This domain method generates the DataProductCreated event
        which triggers update of read models (metrics views).
        """
        self.events.append(
            DataProductCreated(
                product_id=self.product_id,
                pathogen_code=self.pathogen_code,
                pathogen_description=self.pathogen_description,
                timestamp=self.timestamp,
                created_at=datetime.now(timezone.utc),
            )
        )
