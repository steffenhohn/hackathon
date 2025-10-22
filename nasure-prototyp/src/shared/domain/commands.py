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