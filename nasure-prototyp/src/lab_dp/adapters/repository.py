import abc
from typing import Set, List
from sqlalchemy import select
from lab_dp.adapters import orm
from lab_dp.domain import domain


class AbstractRepository(abc.ABC):
    def __init__(self):
        self.seen = set()  # type: Set[domain.LabDataProduct]

    def add(self, product: domain.LabDataProduct) -> str:
        self._add(product)
        self.seen.add(product)
        return product.product_id

    def get(self, product_id) -> domain.LabDataProduct:
        product = self._get(product_id)
        if product:
            self.seen.add(product)
        return product

    def list(self) -> List[domain.LabDataProduct]:
        products = self._list()
        for product in products:
            self.seen.add(product)
        return products

    @abc.abstractmethod
    def _add(self, product: domain.LabDataProduct):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, product_id) -> domain.LabDataProduct:
        raise NotImplementedError

    @abc.abstractmethod
    def _list(self) -> List[domain.LabDataProduct]:
        raise NotImplementedError

class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product):
        self.session.add(product)

    def _get(self, product_id):
        return self.session.query(domain.LabDataProduct).filter_by(product_id=product_id).first()

    def _list(self) -> List[domain.LabDataProduct]:
        return self.session.query(domain.LabDataProduct).all()

