"""Domain events for case mgmt service."""

from dataclasses import dataclass
from datetime import datetime

from shared.domain.commands import Event


@dataclass
class CaseCreated(Event):
    """Event raised when a case has been successfully created."""
    case_id: str            # UUID4 as String
    created_at: datetime    # Timestamp of case creation
    
