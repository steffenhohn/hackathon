"""Repository pattern implementation following Cosmic Python approach."""

import abc
import json
import logging
from io import BytesIO
from typing import Set, Dict, Any, Optional, List
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from fhir_ingestion.domain.model import FhirBundle

logger = logging.getLogger(__name__)


class AbstractMinioRepository(abc.ABC):
    """Abstract repository class"""

    def __init__(self):
        self.seen = set()  # type: Set[FhirBundle]

    def add(self, bundle: FhirBundle) -> str:
        object_key = self._add(bundle)
        self.seen.add(bundle)
        return object_key

    def get(self, object_key: str):
        bundle = self._get(object_key)
        if bundle:
            self.seen.add(bundle)
        return bundle

    def get_by_bundle_id(self, bundle_id: str):
        """Get bundle by bundle ID."""
        return self._get_by_bundle_id(bundle_id) 

    @abc.abstractmethod
    def _add(self, bundle: FhirBundle) -> str:
        """Store FHIR bundle and return object key."""
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve FHIR bundle by object key."""
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_bundle_id(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve FHIR bundle by bundle ID."""
        raise NotImplementedError


class MinIORepository(AbstractMinioRepository):
    """MinIO implementation of the repository pattern."""

    def __init__(self, client: Minio, bucket_name: str = "lab-raw-data"):
        super().__init__()
        self.client = client
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    def _add(self, bundle: FhirBundle) -> str:
        """Store FHIR bundle in MinIO."""
        try:
            # Generate object key with timestamp for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_key = f"fhir_bundles/{timestamp}_{bundle.bundle_id}.json"

            # Convert bundle to JSON bytes
            bundle_json = json.dumps(bundle.bundle_data, indent=2)
            bundle_bytes = BytesIO(bundle_json.encode('utf-8'))

            # Store in MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=bundle_bytes,
                length=len(bundle_json),
                content_type="application/json"
            )

            # Call domain method to mark as stored and generate events
            bundle.store(object_key)

            logger.info(f"Stored FHIR bundle {bundle.bundle_id} at {object_key}")
            return object_key

        except S3Error as e:
            logger.error(f"Failed to store FHIR bundle {bundle.bundle_id}: {e}")
            raise

    def _get(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve FHIR bundle from MinIO."""
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            bundle_json = response.read().decode('utf-8')
            bundle_data = json.loads(bundle_json)

            logger.info(f"Retrieved FHIR bundle from {object_key}")
            return bundle_data

        except S3Error as e:
            logger.error(f"Failed to retrieve FHIR bundle from {object_key}: {e}")
            return None
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()

    def _get_by_bundle_id(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve FHIR bundle by bundle ID from MinIO."""
        try:
            # List objects matching the pattern: fhir_bundles/*_{bundle_id}.json
            prefix = "fhir_bundles/"
            suffix = f"_{bundle_id}.json"

            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)

            for obj in objects:
                if obj.object_name.endswith(suffix):
                    # Found the bundle, retrieve it using existing _get method
                    bundle_data = self._get(obj.object_name)
                    logger.info(f"Retrieved bundle {bundle_id} from {obj.object_name}")
                    return bundle_data

            logger.warning(f"Bundle {bundle_id} not found in MinIO")
            return None

        except S3Error as e:
            logger.error(f"Failed to retrieve bundle {bundle_id}: {e}")
            return None

