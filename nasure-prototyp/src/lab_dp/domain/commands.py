"""Commands for lab data product service."""

from dataclasses import dataclass

from shared.domain.commands import Command


@dataclass
class GenerateDataProduct(Command):
    """Command to generate surveillance data product from stored FHIR bundle."""
    bundle_id: str
    object_key: str