"""Unit of Work implementation for FHIR ingestion service."""

from typing import List
from minio import Minio

from shared.service_layer.unit_of_work import AbstractUnitOfWork
from fhir_ingestion.adapters.repository import MinIORepository
from shared.domain.commands import Event
from config import get_minio_config


class FHIRIngestionUnitOfWork(AbstractUnitOfWork):
    """Unit of Work implementation for FHIR ingestion operations."""

    def __init__(self):
        self._minio_client = None
        self.bundles = None
        self.events: List[Event] = []  # Collect events during transaction

    def __enter__(self):
        # Initialize MinIO client from config
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

        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self._close_connections()

    def collect_new_events(self) -> List[Event]:
        """Collect events from domain entities and clear them."""
        # Collect events from domain entities (like Cosmic Python)
        for bundle in self.bundles.seen:
            while bundle.events:
                self.events.append(bundle.events.pop(0))

        # Return and clear collected events
        events = self.events[:]
        self.events.clear()
        return events

    def _commit(self):
        """Commit changes - MinIO operations are immediately committed."""
        # MinIO operations are immediately committed (no transaction support)
        pass

    def rollback(self):
        """Rollback changes - MinIO doesn't support transactions."""
        # MinIO doesn't support transactions, so can't rollback
        # Clear any pending events
        self.events.clear()

    def _close_connections(self):
        """Close all open connections."""
        # MinIO client doesn't require explicit closing
        self._minio_client = None