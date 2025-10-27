"""FHIR Bundle Transformer - Extract lab data from FHIR bundles."""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import os
import httpx
import config
from lab_dp.domain.domain import LabDataProduct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This sends logs to stdout/stderr
    ]
)
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
            patient_ahv = FHIRTransformer._extract_patient_id(bundle)

            # Extract patient resource from bundle
            patient_resource = FHIRTransformer._extract_patient_resource(bundle)

            # Pseudonymize patient resource
            patient_id = FHIRTransformer._pseudonymize_patient(patient_resource)

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
    def _extract_patient_resource(bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract the complete Patient resource from FHIR bundle.
        
        Returns the full Patient resource that can be sent directly to 
        the pseudonymization API endpoint.
        
        Args:
            bundle: FHIR Bundle dictionary
            
        Returns:
            Complete Patient resource dictionary matching FHIR Patient schema
            
        Raises:
            FHIRTransformationError: If Patient resource not found
        """
        try:
            entries = bundle.get("entry", [])
            
            # Look for Patient resource in bundle entries
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    logger.info(f"Found Patient resource: {resource}")
                    
                    # Return the complete Patient resource as-is
                    # This matches the FHIRPatient model config in the API
                    return resource
            
            # Patient resource not found
            raise FHIRTransformationError("No Patient resource found in bundle")
            
        except Exception as e:
            logger.error(f"Error extracting Patient resource: {e}")
            raise FHIRTransformationError(f"Error extracting Patient resource: {e}") from e

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
                if resource.get("resourceType") == "Observation":
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

    @staticmethod
    def _pseudonymize_patient(patient_resource: Dict[str, Any]) -> str:
        """
        Send Patient resource to pseudonymization API and get patient_id.
        
        Args:
            patient_resource: Complete FHIR Patient resource
            
        Returns:
            patient_id: Pseudonymized patient identifier
            
        Raises:
            FHIRTransformationError: If pseudonymization fails
        """
        try:
            # Get patient service URL from environment
            patient_service_url = config.get_patient_service_api_url()
            endpoint = f"{patient_service_url}/api/v1/patient/pseudonymize"
            
            logger.info(f"Sending Patient resource to pseudonymization API: {endpoint}")
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, json=patient_resource)
                
                if response.status_code == 404:
                    logger.error(f"Patient service not found at {endpoint}")
                    raise FHIRTransformationError("Patient service not available")
                    
                response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
                
                result = response.json()
                patient_id = result.get('patient_id')
                
                if not patient_id:
                    raise FHIRTransformationError("No patient_id returned from pseudonymization service")
                    
                logger.info(f"Successfully pseudonymized patient, got ID: {patient_id}")
                return patient_id
                
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to patient service: {e}")
            raise FHIRTransformationError(f"Patient service connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from patient service: {e}")
            raise FHIRTransformationError(f"Patient service error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Unexpected error in pseudonymization: {e}")
            raise FHIRTransformationError(f"Pseudonymization failed: {e}") from e


class FHIRTransformationError(Exception):
    """Exception raised for errors during FHIR transformation."""
    pass
