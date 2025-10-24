# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


import config
from lab_dp.adapters import repository, fhir_client


class AbstractUnitOfWork(abc.ABC):
    products: repository.AbstractRepository
    fhir_client: fhir_client.AbstractFHIRClient

    def __enter__(self) -> AbstractUnitOfWork:
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        self._commit()

    def collect_new_events(self):
        for product in self.products.seen:
            while product.events:
                yield product.events.pop(0)

    @abc.abstractmethod
    def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError


DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        config.get_postgres_uri(),
        isolation_level="REPEATABLE READ",
    )
)

class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY, fhir_client_impl=None):
        self.session_factory = session_factory
        self.fhir_client_impl = fhir_client_impl or fhir_client.HTTPFHIRClient()

    def __enter__(self):
        self.session = self.session_factory()  # type: Session
        self.products = repository.SqlAlchemyRepository(self.session)
        self.fhir_client = self.fhir_client_impl
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()