"""
Unit tests for repository storage behavior and event generation.
Tests that events are only generated when storage actually succeeds.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from minio.error import S3Error
import json
from io import BytesIO

from fhir_ingestion.adapters.repository import MinIORepository
from fhir_ingestion.domain.model import FhirBundle


class TestMinIORepositoryStorageEvents:
    """Test that events are only generated when MinIO storage succeeds."""

    def test_events_generated_only_after_successful_minio_storage(self):
        """
        Test that bundle.store() is called (generating events) only after
        successful MinIO put_object operation.
        """
        # Arrange
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = None  # Successful storage

        repository = MinIORepository(mock_client, "test-bucket")

        bundle = FhirBundle(
            bundle_id="test-123",
            bundle_data={"resourceType": "Bundle", "id": "test-123"},
            source_system="test-system"
        )

        # Mock the domain store method to track if it was called
        bundle.store = Mock(return_value="test_key")

        # Act
        object_key = repository.add(bundle)

        # Assert
        # 1. MinIO put_object was called
        mock_client.put_object.assert_called_once()
        put_call = mock_client.put_object.call_args

        assert put_call[1]['bucket_name'] == "test-bucket"
        assert 'test-123' in put_call[1]['object_name']
        assert put_call[1]['content_type'] == "application/json"

        # 2. Domain store method was called only after MinIO success
        bundle.store.assert_called_once()
        stored_key = bundle.store.call_args[0][0]
        assert 'test-123' in stored_key

        # 3. Returned object key matches what was stored
        assert object_key == stored_key

    def test_no_events_generated_when_minio_storage_fails(self):
        """
        Test that bundle.store() is NOT called when MinIO put_object fails.
        This ensures no events are generated for failed storage operations.
        """
        # Arrange
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True

        # Simulate MinIO storage failure
        mock_client.put_object.side_effect = S3Error(
            code="AccessDenied",
            message="Access Denied",
            resource="test-bucket",
            request_id="123",
            host_id="456",
            response={}
        )

        repository = MinIORepository(mock_client, "test-bucket")

        bundle = FhirBundle(
            bundle_id="test-456",
            bundle_data={"resourceType": "Bundle", "id": "test-456"},
            source_system="test-system"
        )

        # Mock the domain store method to track if it was called
        bundle.store = Mock()

        # Act & Assert
        with pytest.raises(S3Error):
            repository.add(bundle)

        # Verify that MinIO was attempted
        mock_client.put_object.assert_called_once()

        # Critical: Domain store method should NOT have been called
        bundle.store.assert_not_called()

    def test_minio_storage_content_is_correct(self):
        """
        Test that the content stored in MinIO matches the bundle data.
        """
        # Arrange
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = None

        repository = MinIORepository(mock_client, "test-bucket")

        bundle_data = {
            "resourceType": "Bundle",
            "id": "test-789",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "patient-1"}}
            ]
        }

        bundle = FhirBundle(
            bundle_id="test-789",
            bundle_data=bundle_data,
            source_system="test-system"
        )

        bundle.store = Mock(return_value="mocked_key")

        # Act
        repository.add(bundle)

        # Assert
        mock_client.put_object.assert_called_once()
        put_call = mock_client.put_object.call_args[1]

        # Verify the data content stored in MinIO
        stored_data = put_call['data']
        assert isinstance(stored_data, BytesIO)

        # Read the stored JSON content
        stored_data.seek(0)  # Reset to beginning
        stored_json = stored_data.read().decode('utf-8')
        stored_bundle = json.loads(stored_json)

        assert stored_bundle == bundle_data
        assert stored_bundle["id"] == "test-789"
        assert len(stored_bundle["entry"]) == 1

    def test_object_key_generation_includes_bundle_id(self):
        """
        Test that generated object keys include bundle ID for traceability.
        """
        # Arrange
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = None

        repository = MinIORepository(mock_client, "test-bucket")

        bundle = FhirBundle(
            bundle_id="unique-bundle-999",
            bundle_data={"resourceType": "Bundle"},
            source_system="test-system"
        )

        bundle.store = Mock(return_value="mocked_key")

        # Act
        repository.add(bundle)

        # Assert
        put_call = mock_client.put_object.call_args[1]
        object_name = put_call['object_name']

        # Object key should include bundle ID
        assert "unique-bundle-999" in object_name
        assert object_name.startswith("fhir_bundles/")
        assert object_name.endswith(".json")

        # Bundle.store should have been called with the same key
        bundle.store.assert_called_once_with(object_name)