"""Unit of Work implementation for lab data product service."""

from minio import Minio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.service_layer.unit_of_work import AbstractUnitOfWork
from fhir_ingestion.adapters.repository import MinIORepository
from lab_dp.storage.postgres_repository import PostgreSQLRepository
from config import get_postgres_uri, get_minio_config


DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        get_postgres_uri(),
        isolation_level="REPEATABLE READ",
    )
)


class LabDataProductUnitOfWork(AbstractUnitOfWork):
    """Unit of Work implementation for lab data product operations."""

    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory
        self._minio_client = None
        self._postgres_session = None
        self.bundles = None
        self.postgres_repo = None

    def __enter__(self):
        # Initialize MinIO client from config (for reading stored bundles)
        minio_config = get_minio_config()
        self._minio_client = Minio(
            endpoint=minio_config["endpoint"],
            access_key=minio_config["access_key"],
            secret_key=minio_config["secret_key"],
            secure=minio_config["secure"]
        )
        self.bundles = MinIORepository(
            client=self._minio_client,
            bucket_name=minio_config["bucket_name"]
        )

        # Initialize PostgreSQL session from config
        self._postgres_session = self.session_factory()
        self.postgres_repo = PostgreSQLRepository()

        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self._close_connections()

    def _commit(self):
        """Commit changes across all repositories."""
        # For MinIO, operations are immediately committed (no transaction support)
        # For PostgreSQL, commit the session
        if self._postgres_session:
            self._postgres_session.commit()

    def rollback(self):
        """Rollback changes where possible."""
        # MinIO doesn't support transactions, so can't rollback
        # For PostgreSQL, rollback the session
        if self._postgres_session:
            self._postgres_session.rollback()

    def _close_connections(self):
        """Close all open connections."""
        if self._postgres_session:
            self._postgres_session.close()
            self._postgres_session = None
        # MinIO client doesn't require explicit closing
        self._minio_client = None