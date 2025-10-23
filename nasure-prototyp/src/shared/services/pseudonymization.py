"""Simple pseudonymization functions that return unique UUIDs."""

from __future__ import annotations
from typing import Any, Dict, Optional
from dataclasses import dataclass
from uuid import uuid4
from typing import Dict, Any, Tuple
import re
from shared.storage.patient_repository import PatientRepository, PatientRecord
import logging

_AHV_DIGITS_RE = re.compile(r"\D+")

logger = logging.getLogger(__name__)

@dataclass
class ResolvePatientCommand:
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str  # 'YYYY-MM-DD'
    canton: str

class PatientService:
    def __init__(self, repo: PatientRepository):
        self.repo = repo

    def normalize_ahv(self, ahv: str) -> str:
        """Removes non-digit characters from AHV number."""
        digits = _AHV_DIGITS_RE.sub("", ahv or "")
        if not digits or not digits.isdigit():
            raise ValueError("Invalid AHV number: {ahv}")
        return digits

    def pseudonymize_patient(self, patient_resource: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Pseudonymize FHIR Patient resource.
        Check if patient with same AHV exists; if so, return existing patient_id.
        If not, create new patient_id. 

        Args:
            patient_resource: FHIR Patient resource

        Returns:
            Tuple of (patient_id, created)
        """
        
        # check if patient exists by AHV
        patient_data = self.extract_patient_data(patient_resource)
        patient_id = self.repo.get_patient_id_by_ahv(patient_data["ahv_number"])

        if patient_id:
            return patient_id, False  # existing patient
        else:
            # create new patient
            new_patient_id = str(uuid4())
            new_patient = PatientRecord(
                new_patient_id,
                ahv_number=patient_data["ahv_number"],
                family_name=patient_data["family_name"],
                given_name=patient_data["given_name"],
                gender=patient_data["gender"],
                birthdate=patient_data["birthdate"],
                canton=patient_data["canton"],
            )
            pid, created = self.repo.upsert_patient_by_ahv(new_patient)
            if created:
                return new_patient_id, True # new patient created
            else:
                raise Exception("Failed to create new patient record.")


    def extract_ahv(self, patient: Dict[str, Any]) -> str:
        """
        Try to read the AHV from identifier slice 'AHVN13'.
        else accept any identifier that looks like a 13-digit Swiss AHV (often starting with '756').
        Return: AHV number digits-only.
        """
        identifier = patient.get("identifier") or []
        ahv_string = (identifier[0].get("value") or "").strip()
        ahv_number = self.normalize_ahv(ahv_string)
        if len(ahv_number) == 13 and ahv_number.isdigit():
            logger.debug(f"Extracted AHV number: {ahv_number}")
            return ahv_number
        
        raise ValueError("AHV number not found in Patient.identifier (AHVN13).")


    def extract_name(self, patient: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract names (family and given) from Patient record
        Returns: (family_name, given_name)
        """
        names = patient.get("name") or []
        if not names:
            raise ValueError("Patient.name is required.")
        nm = names[0]
        family_name = (nm.get("family") or "").strip()
        given_name = (nm.get("given") or "").strip()
        if family_name and given_name:
            logger.debug(f"Extracted Patient name: {family_name}, {given_name}")
            return family_name, given_name  
        
        raise ValueError("Patient.name.family and Patient.name.given are required.")
        
    def extract_gender(self, patient: Dict[str, Any]) -> str:
        """
        Extract gender from Patient record
        Returns: gender string
        """
        gender = (patient.get("gender") or "").strip().lower()
        # CH ELM allows male|female|other|unknown, but your DB constraint is male/female.
        if gender: 
            logger.debug(f"Extracted Patient gender: {gender}")
            return gender
        
        raise ValueError("Patient.gender are required.")

    def extract_birthdate(self, patient: Dict[str, Any]) -> str:
        """
        Extract birthdate from Patient record
        Returns: birthdate as 'YYYY-MM-DD'
        """    
        # CH ELM constraint: at least YYYY-MM-DD
        bd = (patient.get("birthDate") or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", bd):
            raise ValueError("Patient.birthDate must be in format YYYY-MM-DD.")
        
        logger.debug(f"Extracted Patient birthdate: {bd}")
        return bd

    def extract_canton(self, patient: Dict[str, Any]) -> str:
        """
        Extract canton from Patient record
        Returns: canton as 2-letter abbreviation
        """ 
        address = patient.get("address") or []
        if not address:
            raise ValueError("Patient.address is required.")
        canton = (address[0].get("state") or "").strip().upper()
        if not canton:
            raise ValueError("Patient.address.home.state (canton) is required.")
        
        logger.debug(f"Extracted Patient canton: {canton}")
        return canton

    def extract_patient_data(self, patient: Dict[str, Any]) -> dict:
        """
        Takes a FHIR 'patient' resourceType as input and extracts relevant fields.
        Returns: patient dict
        """
        ahv = self.extract_ahv(patient)
        family, given = self.extract_name(patient)
        gender = self.extract_gender(patient)
        birthdate = self.extract_birthdate(patient)
        canton = self.extract_canton(patient)
        return {
            "ahv_number": ahv,
            "family_name": family,
            "given_name": given,
            "gender": gender,
            "birthdate": birthdate,
            "canton": canton,
        }