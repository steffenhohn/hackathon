"""
Minimal CH-eLM FHIR Transformer
Converts CH-eLM FHIR Bundle to clean surveillance domain model
"""
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

from lab_dp.domain.minimal_model import (
    LaboratoryReport, LaboratoryObservation, TestCode, TestResult, Specimen,
    ResultInterpretation, CH_ELM_PATHOGEN_MAPPINGS, SNOMED_RESULT_MAPPINGS
)


class MinimalFHIRTransformer:
    """Minimal transformer for CH-eLM FHIR documents"""

    def transform_bundle(self, fhir_bundle: Dict[str, Any]) -> LaboratoryReport:
        """Transform CH-eLM FHIR Bundle to LaboratoryReport"""

        # Extract resources by type
        resources = self._extract_resources(fhir_bundle)

        # Create report with basic info from Bundle
        report = LaboratoryReport(
            bundle_id=fhir_bundle.get("id", ""),
            fhir_identifier=self._get_bundle_identifier(fhir_bundle),
            report_timestamp=self._parse_timestamp(fhir_bundle.get("timestamp")),
            source_system="ch-elm"
        )

        # Set composition date if available
        composition = resources.get("compositions", [{}])[0]
        if composition:
            report.composition_date = self._parse_timestamp(composition.get("date"))
            report.report_status = composition.get("status", "final")

        # Extract clean entity IDs
        report.patient_id = self._extract_patient_id(resources.get("patients", [{}])[0])
        report.performing_lab_id = self._extract_lab_gln(resources.get("organizations", []))
        report.ordering_facility_id = self._extract_ordering_facility_gln(resources)

        # Transform observations
        for observation in resources.get("observations", []):
            lab_obs = self._transform_observation(observation, resources)
            if lab_obs:
                report.add_observation(lab_obs)

        # Set primary pathogen at report level
        report.pathogen = self._extract_primary_pathogen(report.observations)

        return report

    def _extract_resources(self, bundle: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract resources by type from FHIR Bundle (CH-eLM compliant)"""
        resources = {
            "compositions": [],
            "diagnostic_reports": [],
            "patients": [],
            "observations": [],
            "specimens": [],
            "service_requests": [],
            "practitioner_roles": [],
            "practitioners": [],
            "organizations": []
        }

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType", "").lower()

            if resource_type == "composition":
                resources["compositions"].append(resource)
            elif resource_type == "diagnosticreport":
                resources["diagnostic_reports"].append(resource)
            elif resource_type == "patient":
                resources["patients"].append(resource)
            elif resource_type == "observation":
                resources["observations"].append(resource)
            elif resource_type == "specimen":
                resources["specimens"].append(resource)
            elif resource_type == "servicerequest":
                resources["service_requests"].append(resource)
            elif resource_type == "practitionerrole":
                resources["practitioner_roles"].append(resource)
            elif resource_type == "practitioner":
                resources["practitioners"].append(resource)
            elif resource_type == "organization":
                resources["organizations"].append(resource)

        return resources

    def _get_bundle_identifier(self, bundle: Dict[str, Any]) -> str:
        """Extract Bundle identifier value"""
        identifier = bundle.get("identifier", {})
        return identifier.get("value", "")

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse FHIR timestamp string"""
        if not timestamp_str:
            return None

        try:
            # Handle different timestamp formats
            if "T" in timestamp_str:
                if timestamp_str.endswith("Z"):
                    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    return datetime.fromisoformat(timestamp_str)
            else:
                return datetime.fromisoformat(timestamp_str + "T00:00:00+00:00")
        except ValueError:
            return None

    def _extract_patient_id(self, patient: Dict[str, Any]) -> str:
        """Create clean patient identifier (hashed)"""
        if not patient:
            return ""

        # Use AHV number if available (Swiss national identifier)
        identifiers = patient.get("identifier", [])
        for identifier in identifiers:
            if "2.16.756.5.32" in identifier.get("system", ""):
                ahv_number = identifier.get("value", "")
                if ahv_number:
                    # Hash for privacy
                    return f"PAT_{hashlib.sha256(ahv_number.encode()).hexdigest()[:12]}"

        # Fallback to patient ID
        patient_id = patient.get("id", "")
        return f"PAT_{hashlib.sha256(patient_id.encode()).hexdigest()[:12]}" if patient_id else ""

    def _extract_lab_gln(self, organizations: List[Dict[str, Any]]) -> str:
        """Extract performing laboratory GLN"""
        for org in organizations:
            org_name = org.get("name", "")
            if "Lab" in org_name or "labor" in org_name.lower():
                identifiers = org.get("identifier", [])
                for identifier in identifiers:
                    # GLN system
                    if "2.51.1.3" in identifier.get("system", ""):
                        return identifier.get("value", "")

        return ""

    def _extract_ordering_facility_gln(self, resources: Dict[str, List]) -> Optional[str]:
        """Extract ordering facility GLN from ServiceRequest → PractitionerRole → Organization chain"""

        # Find ServiceRequest
        service_requests = resources.get("service_requests", [])
        if not service_requests:
            return None

        service_request = service_requests[0]  # Take first one

        # Get requester reference (PractitionerRole)
        requester_ref = service_request.get("requester", {}).get("reference", "")
        if not requester_ref:
            return None

        # Extract PractitionerRole ID
        practitioner_role_id = requester_ref.split("/")[-1]

        # Find the PractitionerRole
        practitioner_roles = resources.get("practitioner_roles", [])
        target_role = None
        for role in practitioner_roles:
            if role.get("id") == practitioner_role_id:
                target_role = role
                break

        if not target_role:
            return None

        # Get organization reference
        org_ref = target_role.get("organization", {}).get("reference", "")
        if not org_ref:
            return None

        org_id = org_ref.split("/")[-1]

        # Find the Organization and extract GLN
        organizations = resources.get("organizations", [])
        for org in organizations:
            if org.get("id") == org_id:
                identifiers = org.get("identifier", [])
                for identifier in identifiers:
                    # Hospital/clinic identifier system
                    if "2.16.756.5.45" in identifier.get("system", ""):
                        return identifier.get("value", "")

        return None

    def _extract_primary_pathogen(self, observations: List) -> str:
        """Extract primary pathogen from observations for report-level classification"""
        if not observations:
            return ""

        # Get all unique pathogens
        pathogens = [obs.test_code.pathogen for obs in observations if obs.test_code.pathogen]

        if not pathogens:
            return ""

        # For surveillance, typically one pathogen per report
        # If multiple, take the first one (could be enhanced with priority logic)
        return pathogens[0]

    def _transform_observation(self, observation: Dict[str, Any], resources: Dict[str, List]) -> Optional[LaboratoryObservation]:
        """Transform FHIR Observation to LaboratoryObservation"""

        # Extract test code (LOINC)
        test_code = self._extract_test_code(observation)
        if not test_code:
            return None

        # Extract result interpretation
        result = self._extract_test_result(observation)

        # Extract timing
        test_date = self._parse_timestamp(observation.get("effectiveDateTime"))

        # Extract specimen info
        specimen = self._extract_specimen_info(observation, resources)

        return LaboratoryObservation(
            observation_id=observation.get("id", ""),
            test_code=test_code,
            result=result,
            test_date=test_date,
            specimen=specimen
        )

    def _extract_test_code(self, observation: Dict[str, Any]) -> Optional[TestCode]:
        """Extract LOINC test code and map to pathogen"""
        code_obj = observation.get("code", {})
        codings = code_obj.get("coding", [])

        for coding in codings:
            if coding.get("system") == "http://loinc.org":
                loinc_code = coding.get("code", "")
                loinc_display = coding.get("display", "")

                # Map to pathogen
                pathogen = CH_ELM_PATHOGEN_MAPPINGS.get(loinc_code, "unknown")

                if pathogen != "unknown":
                    return TestCode(
                        loinc_code=loinc_code,
                        loinc_display=loinc_display,
                        pathogen=pathogen
                    )

        return None

    def _extract_test_result(self, observation: Dict[str, Any]) -> TestResult:
        """Extract test result interpretation"""

        # Check valueCodeableConcept (SNOMED)
        value_concept = observation.get("valueCodeableConcept", {})
        if value_concept:
            codings = value_concept.get("coding", [])
            for coding in codings:
                if coding.get("system") == "http://snomed.info/sct":
                    snomed_code = coding.get("code", "")
                    snomed_display = coding.get("display", "")

                    # Map SNOMED to interpretation
                    interpretation = SNOMED_RESULT_MAPPINGS.get(
                        snomed_code, ResultInterpretation.INCONCLUSIVE
                    )

                    return TestResult(
                        interpretation=interpretation,
                        snomed_code=snomed_code,
                        snomed_display=snomed_display
                    )

        # Fallback to interpretation field
        interpretations = observation.get("interpretation", [])
        for interp in interpretations:
            codings = interp.get("coding", [])
            for coding in codings:
                code = coding.get("code", "").upper()
                if code == "POS":
                    return TestResult(interpretation=ResultInterpretation.POSITIVE)
                elif code == "NEG":
                    return TestResult(interpretation=ResultInterpretation.NEGATIVE)

        return TestResult(interpretation=ResultInterpretation.INCONCLUSIVE)

    def _extract_specimen_info(self, observation: Dict[str, Any], resources: Dict[str, List]) -> Optional[Specimen]:
        """Extract basic specimen information"""
        # Find specimen referenced by observation
        specimen_ref = observation.get("specimen", {}).get("reference", "")
        if not specimen_ref:
            return None

        specimen_id = specimen_ref.split("/")[-1]

        # Find specimen resource
        for specimen_resource in resources.get("specimens", []):
            if specimen_resource.get("id") == specimen_id:
                collection = specimen_resource.get("collection", {})
                collection_date = self._parse_timestamp(collection.get("collectedDateTime"))

                return Specimen(collection_date=collection_date)

        return None