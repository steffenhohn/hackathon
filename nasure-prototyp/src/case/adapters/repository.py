import abc
from case.domain import domain
from typing import List
import logging

logger = logging.getLogger(__name__)


class AbstractRepository(abc.ABC):
    def __init__(self):
        self.seen = set() 

    def add(self, case: domain.CaseRecord) -> str:
        self._add(case)
        self.seen.add(case)
        return case.case_id

    def get(self, case_id) -> domain.CaseRecord:
        case = self._get(case_id)
        if case:
            self.seen.add(case)
        return case

    def get_cases_by_patient_and_pathogen(self, patient_id: str, pathogen_code: str) -> List[domain.CaseRecord]:
        cases = self._get_cases_by_patient_and_pathogen(patient_id, pathogen_code)
        for case in cases:
            self.seen.add(case)
        return cases

    @abc.abstractmethod
    def _add(self, case: domain.CaseRecord):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, case_id) -> domain.CaseRecord:
        raise NotImplementedError
    
    @abc.abstractmethod
    def _get_cases_by_patient_and_pathogen(self, patient_id: str, pathogen_code: str) -> List[domain.CaseRecord]:
         raise NotImplementedError

class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, case):
        self.session.add(case)

    def _get(self, case_id):
        return self.session.query(domain.CaseRecord).filter_by(case_id=case_id).first()
    
    def _get_cases_by_patient_and_pathogen(self, patient_id: str, pathogen_code: str) -> List[domain.CaseRecord]:
        """Get all cases for a specific patient and pathogen."""
        return self.session.query(domain.CaseRecord)\
            .filter(domain.CaseRecord.patient_id == patient_id)\
            .filter(domain.CaseRecord.pathogen == pathogen_code)\
            .all()
