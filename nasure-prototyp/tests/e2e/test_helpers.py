"""Test helper functions for e2e tests"""
import json
import time
from typing import Dict, Any, List
from minio import Minio

from config import get_minio_config


def wait_for_bundle_storage(minio_client: Minio, bundle_id: str, timeout: int = 10) -> bool:
    """Wait for bundle to appear in MinIO storage"""
    minio_config = get_minio_config()
    bucket_name = minio_config["bucket_name"]

    start_time = time.time()
    while time.time() - start_time < timeout:
        objects = list(minio_client.list_objects(bucket_name, recursive=True))
        bundle_objects = [obj for obj in objects if bundle_id in obj.object_name]

        if bundle_objects:
            return True

        time.sleep(0.5)

    return False


def get_stored_bundle(minio_client: Minio, bundle_id: str) -> Dict[str, Any]:
    """Retrieve stored bundle from MinIO"""
    minio_config = get_minio_config()
    bucket_name = minio_config["bucket_name"]

    objects = list(minio_client.list_objects(bucket_name, recursive=True))
    bundle_objects = [obj for obj in objects if bundle_id in obj.object_name]

    if not bundle_objects:
        raise ValueError(f"Bundle {bundle_id} not found in storage")

    stored_object = bundle_objects[0]
    response = minio_client.get_object(bucket_name, stored_object.object_name)
    return json.loads(response.read().decode('utf-8'))


def count_stored_bundles(minio_client: Minio) -> int:
    """Count total bundles stored in MinIO"""
    minio_config = get_minio_config()
    bucket_name = minio_config["bucket_name"]

    objects = list(minio_client.list_objects(bucket_name, recursive=True))
    return len(objects)


def create_minimal_fhir_bundle(bundle_id: str = "test-bundle") -> Dict[str, Any]:
    """Create minimal valid FHIR bundle for testing"""
    from tests.examples.fhir_loader import fhir_examples
    return fhir_examples.create_bundle_with_id("minimal_bundle.json", bundle_id)


def assert_bundle_stored_correctly(minio_client: Minio, bundle_id: str, expected_entry_count: int = None):
    """Assert that bundle is stored correctly in MinIO"""
    stored_bundle = get_stored_bundle(minio_client, bundle_id)

    assert stored_bundle["resourceType"] == "Bundle"
    assert stored_bundle["id"]

    if expected_entry_count is not None:
        assert len(stored_bundle["entry"]) == expected_entry_count