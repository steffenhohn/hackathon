import abc
from case.domain import domain
from case.adapters.orm import case_to_products
from typing import List, Tuple, Optional
import logging
from datetime import datetime, timezone
from sqlalchemy import desc

logger = logging.getLogger(__name__)

class AbstractRepository(abc.ABC):
    def __init__(self):
        self.seen = set() 

    def link_product_to_case(self, case_id: str, product_id: str, is_original:bool = False ) -> domain.CaseToProductRecord:
        caseToProductRecord = self._link_product_to_case(case_id, product_id, is_original)
        self.seen.add(caseToProductRecord)
        return caseToProductRecord

    def get_products_for_case(self, case_id: str) -> List[domain.CaseToProductRecord]:
        """ Get all products linked to a case (1:M relationship)"""
        products = self._get_products_for_case(case_id)
        for product in products:
            self.seen.add(product)
        return products

    def get_case_for_product(self, product_id: str) -> domain.CaseToProductRecord:
        """ Get the case linked to a product (1:1 relationship)"""
        case = self._get_case_for_product(product_id)
        if case:
            self.seen.add(case)
        return case

    @abc.abstractmethod
    def _link_product_to_case(self, case_id: str, product_id: str, is_original:bool = False ) -> domain.CaseToProductRecord:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_products_for_case(self, case_id: str) -> List[domain.CaseToProductRecord]:
        raise NotImplementedError
    
    @abc.abstractmethod
    def _get_case_for_product(self, product_id: str) -> domain.CaseToProductRecord:
        raise NotImplementedError

    # @abc.abstractmethod
    # def _remove_product_link(self, case_id: str, product_id: str) -> bool:
    #     raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """Repository for managing case-product relationships"""
    
    def __init__(self, session):
        super().__init__()
        self.session = session
    
    def _link_product_to_case(
        self, 
        case_id: str, 
        product_id: str, 
        is_original: bool = False
    ) -> domain.CaseToProductRecord:
        """Create a link between a case and a product"""
        
        # Check if link already exists
        existing = self.session.query(domain.CaseToProductRecord).filter_by(
            case_id=case_id,
            product_id=product_id
        ).first()
        
        if existing:
            # Return existing link
            return domain.CaseToProductRecord(
                case_id=existing.case_id,
                product_id=existing.product_id,
                is_original=existing.is_original,
                linked_at=existing.linked_at
            )
        
        # Create new link
        new_link = domain.CaseToProductRecord(
            case_id=case_id,
            product_id=product_id,
            is_original=is_original,
            linked_at=datetime.now(timezone.utc)
        )

        self.session.add(new_link)
        
        return new_link
    
    def _get_products_for_case(self, case_id: str) -> List[domain.CaseToProductRecord]:
        """Get all products linked to a case"""
        links = self.session.query(domain.CaseToProductRecord).filter_by(case_id=case_id).order_by(desc(case_to_products.c.linked_at)).all()
        
        return [
            domain.CaseToProductRecord(
                case_id=link.case_id,
                product_id=link.product_id,
                is_original=link.is_original,
                linked_at=link.linked_at
            )
            for link in links
        ]
    
    def _get_case_for_product(self, product_id: str) -> Optional[domain.CaseToProductRecord]:
        """Get case linked to a product"""
        link = self.session.query(domain.CaseToProductRecord).filter_by(product_id=product_id).first()
        
        if not link:
            return None

        return domain.CaseToProductRecord(
                case_id=link.case_id,
                product_id=link.product_id,
                is_original=link.is_original,
                linked_at=link.linked_at
            )
    