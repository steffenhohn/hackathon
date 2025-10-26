import abc
from case.domain import domain
from case.adapters.orm import cases
from typing import List, Tuple, Optional
import logging
from sqlalchemy import and_, or_

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

    def get_all_cases_paginated(
            self, 
            page: int, 
            page_size: int,
            status_filter: Optional[str] = None,
            pathogen_code_filter: Optional[str] = None,
            canton_filter: Optional[str] = None,
            patient_id_filter: Optional[str] = None
        ) -> Tuple[List[domain.CaseRecord], int]:
        cases, count = self._get_all_cases_paginated(
            page, 
            page_size,
            status_filter,
            pathogen_code_filter,
            canton_filter,
            patient_id_filter
        )
        for case in cases:
            self.seen.add(case)
        return cases, count

    @abc.abstractmethod
    def _add(self, case: domain.CaseRecord):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, case_id) -> domain.CaseRecord:
        raise NotImplementedError
    
    @abc.abstractmethod
    def _get_all_cases_paginated(
        self, 
        page: int, 
        page_size: int,
        status_filter: Optional[str] = None,
        pathogen_code_filter: Optional[str] = None,
        canton_filter: Optional[str] = None,
        patient_id_filter: Optional[str] = None   
    ) -> Tuple[List[domain.CaseRecord], int]:
        raise NotImplementedError

class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, case):
        self.session.add(case)

    def _get(self, case_id):
        return self.session.query(domain.CaseRecord).filter_by(case_id=case_id).first()
    
    def _get_all_cases_paginated(
        self, 
        page: int, 
        page_size: int,
        status_filter: Optional[str] = None,
        pathogen_code_filter: Optional[str] = None,
        canton_filter: Optional[str] = None,
        patient_id_filter: Optional[str] = None
    ) -> Tuple[List[domain.CaseRecord], int]:
        """
        Get paginated cases with optional filtering.
        
        Returns:
            Tuple of (cases_list, total_count)
        """
        query = self.session.query(domain.CaseRecord)
        
        # Apply status filter
        if status_filter and status_filter != "all":
            if status_filter == "not_closed":
                # Exclude closed/archived cases
                query = query.filter(
                    ~domain.CaseRecord.status.in_(["abgeschlossen", "archiviert"])
                )
            else:
                # Filter by specific status
                query = query.filter(domain.CaseRecord.status == status_filter)
        
        # Apply other filters
        if pathogen_code_filter:
            query = query.filter(domain.CaseRecord.pathogen_code.ilike(f"%{pathogen_code_filter}%"))
        
        if canton_filter:
            query = query.filter(domain.CaseRecord.canton == canton_filter)
            
        if patient_id_filter:
            query = query.filter(domain.CaseRecord.patient_id == patient_id_filter)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        cases = query.order_by(domain.CaseRecord.created_at.desc())\
                    .offset(offset)\
                    .limit(page_size)\
                    .all()
        
        return cases, total_count