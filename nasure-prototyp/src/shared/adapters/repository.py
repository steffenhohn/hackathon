import abc
from typing import Set, Tuple, Optional
from shared.domain import domain

import logging

logger = logging.getLogger(__name__)


class AbstractRepository(abc.ABC):
    def __init__(self):
        self.seen = set()  # type: Set[domain.PatientRecord]

    def add(self, patient: domain.PatientRecord) -> str:
        self._add(patient)
        self.seen.add(patient)
        return patient.patient_id

    def get(self, patient_id) -> domain.PatientRecord:
        patient = self._get(patient_id)
        if patient:
            self.seen.add(patient)
        return patient

    def get_patient_id_by_ahv(self, ahv) -> Optional[str]:
        patient_id = self._get_patient_id_by_ahv(ahv)
        return patient_id
    
    def get_patient_details_by_patient_id(self, patient_id) -> domain.PatientRecord:
        patient_record = self._get_patient_details_by_patient_id(patient_id)
        return patient_record
    
    def upsert_patient_by_ahv(self, patient_record: domain.PatientRecord) -> Tuple[str, bool]:
        patient_id, created = self._upsert_patient_by_ahv(patient_record)
        return patient_id, created

    @abc.abstractmethod
    def _add(self, patient: domain.PatientRecord):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, patient_id) -> domain.PatientRecord:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_patient_id_by_ahv(self, ahv) -> str:
        raise NotImplementedError
    
    @abc.abstractmethod
    def _get_patient_details_by_patient_id(self, patient_id) -> domain.PatientRecord:
        raise NotImplementedError
    
    @abc.abstractmethod
    def _upsert_patient_by_ahv(self, patient_record: domain.PatientRecord) -> Tuple[str, bool]:
        raise NotImplementedError

class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, patient):
        self.session.add(patient)

    def _get(self, patient_id):
        return self.session.query(domain.PatientRecord).filter_by(patient_id=patient_id).first()
    
    def _get_patient_id_by_ahv(self, ahv):
        patient = self.session.query(domain.PatientRecord).filter_by(ahv_number=ahv).first()
        if patient:
            return patient.patient_id
        else:
            return None

    def _get_patient_details_by_patient_id(self, patient_id) -> domain.PatientRecord:
        patient_record = self.session.query(domain.PatientRecord).filter_by(patient_id=patient_id).first()
        return patient_record

    def _upsert_patient_by_ahv(self, patient_record: domain.PatientRecord) -> Tuple[str, bool]:
        """
        Upsert patient using SQLAlchemy.
        Returns: (patient_id, was_inserted)
        """
        try:
            # Check if patient exists, get the actual patient record, not just the ID
            existing_patient = self.session.query(domain.PatientRecord).filter_by(ahv_number=patient_record.ahv_number).first()
            
            if existing_patient:
                # Update existing patient (keep original patient_id)
                existing_patient.family_name = patient_record.family_name
                existing_patient.given_name = patient_record.given_name
                existing_patient.gender = patient_record.gender
                existing_patient.birthdate = patient_record.birthdate
                existing_patient.canton = patient_record.canton
                
                self.session.add(existing_patient)  # Mark for update
                return existing_patient.patient_id, False  # Not inserted, updated
            else:
                # Insert new patient
                self.session.add(patient_record)
                return patient_record.patient_id, True  # Inserted
                
        except Exception as e:
            logger.error(f"Database error upserting patient AHV {patient_record.ahv_number}: {e}")
            raise