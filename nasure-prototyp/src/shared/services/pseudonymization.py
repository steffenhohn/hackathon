"""Simple pseudonymization functions that return unique UUIDs."""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from uuid import uuid4
import re
import os
from shared.adapters import orm
from shared.domain.domain import PatientRecord
from shared.adapters.repository import AbstractRepository 
import logging

_AHV_DIGITS_RE = re.compile(r"\D+")

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PatientService:
    def __init__(self, repo: AbstractRepository):
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
        logger.info(f"Pseudonymizing patient:"f"{patient_data}")

        patient_id = self.repo.get_patient_id_by_ahv(patient_data["ahv_number"])

        if patient_id:
            logger.info(f"Found existing patient_id: {patient_id} for AHV:"f"{patient_data['ahv_number']}")
            return patient_id, False  # existing patient
        else:
            logger.info(f"No existing patient found for AHV:"f"{patient_data['ahv_number']}. Creating new record.")
            # create new patient
            new_patient_id = str(uuid4())

            new_patient = PatientRecord(
                patient_id=new_patient_id,
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
        if isinstance(names, list): 
            name = names[0]  # Take first name
            family_name = name.get('family', '').strip()
            given_names = name.get('given', [])
        
        if isinstance(given_names, list) and given_names:
            given_name = given_names[0].strip()  # Take first given name
               
        if family_name and given_name:
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