"""FHIR Bundle Transformer - Extract lab data from FHIR bundles."""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from lab_dp.domain.domain import LabDataProduct

logger = logging.getLogger(__name__)


class FHIRTransformer:
    """Transform FHIR bundles into LabDataProduct domain entities."""

    @staticmethod
    def extract_lab_data_product(bundle: Dict[str, Any], bundle_id: str, stored_at: datetime = None) -> LabDataProduct:
        """
        Extract lab surveillance data from FHIR bundle.

        Args:
            bundle: FHIR Bundle dictionary
            bundle_id: The bundle identifier
            stored_at: When the bundle was stored by fhir_ingestion (optional)

        Returns:
            LabDataProduct domain entity

        Raises:
            FHIRTransformationError: If required data cannot be extracted
        """
        try:
            logger.info(f"Transforming bundle {bundle_id}")

            # Extract patient ID from bundle
            patient_id = FHIRTransformer._extract_patient_id(bundle)

            # Extract timestamp from bundle
            timestamp = FHIRTransformer._extract_timestamp(bundle)

            # Extract pathogen information from Observation resources
            pathogen_info = FHIRTransformer._extract_pathogen_info(bundle)

            # Generate product ID
            product_id = str(uuid.uuid4())

            product = LabDataProduct(
                product_id=product_id,
                patient_id=patient_id,
                bundle_id=bundle_id,
                timestamp=timestamp,
                pathogen_code=pathogen_info["code"],
                pathogen_description=pathogen_info["description"],
                interpretation=pathogen_info["interpretation"],
                stored_at=stored_at,
                version_number=1
            )

            logger.info(f"Successfully transformed bundle {bundle_id} to product {product_id}")
            return product

        except Exception as e:
            logger.error(f"Failed to transform bundle {bundle_id}: {e}")
            raise FHIRTransformationError(f"Transformation failed: {e}") from e

    @staticmethod
    def _extract_patient_id(bundle: Dict[str, Any]) -> str:
        """Extract patient identifier from bundle."""
        try:
            # Look for Patient resource in bundle entries
            entries = bundle.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    # Get patient identifier
                    identifiers = resource.get("identifier", [])
                    if identifiers:
                        return identifiers[0].get("value", "UNKNOWN")

            # Fallback: look in DiagnosticReport subject
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "DiagnosticReport":
                    subject = resource.get("subject", {})
                    reference = subject.get("reference", "")
                    if "Patient/" in reference:
                        return reference.split("Patient/")[1]

            raise FHIRTransformationError("No patient identifier found in bundle")

        except Exception as e:
            raise FHIRTransformationError(f"Error extracting patient ID: {e}") from e

    @staticmethod
    def _extract_timestamp(bundle: Dict[str, Any]) -> str:
        """Extract effective timestamp from bundle."""
        try:
            # Look for DiagnosticReport effectiveDateTime
            entries = bundle.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "DiagnosticReport":
                    effective_dt = resource.get("effectiveDateTime")
                    if effective_dt:
                        return effective_dt

            # Fallback to bundle timestamp or current time
            bundle_timestamp = bundle.get("timestamp")
            if bundle_timestamp:
                return bundle_timestamp

            # Last resort: current timestamp
            return datetime.utcnow().isoformat()

        except Exception as e:
            raise FHIRTransformationError(f"Error extracting timestamp: {e}") from e

    @staticmethod
    def _extract_pathogen_info(bundle: Dict[str, Any]) -> Dict[str, str]:
        """Extract pathogen code, description, and interpretation from Observation resources."""
        try:
            entries = bundle.get("entry", [])

            # Look for Observation resources with lab results
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Observation":
                    # Get code (pathogen identification)
                    code_obj = resource.get("code", {})
                    coding = code_obj.get("coding", [])
                    if coding:
                        pathogen_code = coding[0].get("code", "UNKNOWN")
                        pathogen_description = coding[0].get("display", "Unknown pathogen")
                    else:
                        pathogen_code = "UNKNOWN"
                        pathogen_description = "Unknown pathogen"

                    # Get interpretation (positive/negative/etc)
                    interpretation_obj = resource.get("interpretation", [])
                    if interpretation_obj:
                        interp_coding = interpretation_obj[0].get("coding", [])
                        if interp_coding:
                            interpretation = interp_coding[0].get("code", "UNKNOWN")
                        else:
                            interpretation = "UNKNOWN"
                    else:
                        interpretation = "UNKNOWN"

                    return {
                        "code": pathogen_code,
                        "description": pathogen_description,
                        "interpretation": interpretation
                    }

            # If no observation found, return defaults
            logger.warning("No Observation resource found in bundle, using defaults")
            return {
                "code": "UNKNOWN",
                "description": "No pathogen data found",
                "interpretation": "UNKNOWN"
            }

        except Exception as e:
            raise FHIRTransformationError(f"Error extracting pathogen info: {e}") from e


class FHIRTransformationError(Exception):
    """Exception raised for errors during FHIR transformation."""
    pass
