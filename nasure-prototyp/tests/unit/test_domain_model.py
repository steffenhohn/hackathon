"""Unit tests for FHIR domain model following Cosmic Python patterns"""
import pytest
from datetime import datetime, timezone

from fhir_ingestion.domain.model import FhirBundle
from fhir_ingestion.domain.events import BundleStored


def test_fhir_bundle_creation():
    """Test basic FhirBundle creation"""
    bundle_data = {
        "resourceType": "Bundle",
        "id": "test-bundle-001"
    }

    bundle = FhirBundle(
        bundle_id="test-001",
        bundle_data=bundle_data,
        bundle_type="test-type",
        source_system="test-system"
    )

    assert bundle.bundle_id == "test-001"
    assert bundle.bundle_data == bundle_data
    assert bundle.source_system == "test-system"
    assert bundle.stored_at is None
    assert bundle.object_key is None
    assert len(bundle.events) == 0


def test_fhir_bundle_store_generates_events():
    """Test that storing bundle generates domain events"""
    bundle_data = {"resourceType": "Bundle", "id": "test-bundle-001"}

    bundle = FhirBundle(
        bundle_id="test-001",
        bundle_data=bundle_data,
        bundle_type="test-type",
        source_system="test-system"
    )

    # Act - store the bundle
    object_key = "fhir_bundles/20240115_103000_test-001.json"
    result = bundle.store(object_key)

    # Assert - bundle state updated
    assert result == object_key
    assert bundle.object_key == object_key
    assert bundle.stored_at is not None
    assert isinstance(bundle.stored_at, datetime)

    # Assert - events generated
    assert len(bundle.events) == 1

    # Check BundleStored event
    bundle_stored_event = bundle.events[0]
    assert isinstance(bundle_stored_event, BundleStored)
    assert bundle_stored_event.bundle_id == "test-001"
    assert bundle_stored_event.object_key == object_key
    assert bundle_stored_event.source_system == "test-system"
    assert bundle_stored_event.stored_at == bundle.stored_at
    assert bundle_stored_event.bundle_size == 0
    assert bundle_stored_event.metadata == {}


def test_fhir_bundle_can_only_be_stored_once():
    """Test that bundle can be stored multiple times (updates object_key)"""
    bundle_data = {"resourceType": "Bundle", "id": "test-bundle-001"}

    bundle = FhirBundle(
        bundle_id="test-001",
        bundle_data=bundle_data,
        bundle_type="test-type",
        source_system="test-system"
    )

    # First store
    object_key1 = "fhir_bundles/20240115_103000_test-001.json"
    bundle.store(object_key1)

    assert bundle.object_key == object_key1
    assert len(bundle.events) == 1

    # Second store (e.g., retry scenario)
    object_key2 = "fhir_bundles/20240115_103001_test-001.json"
    bundle.store(object_key2)

    # Bundle state should be updated
    assert bundle.object_key == object_key2
    # Should have 2 events now (1 from each store)
    assert len(bundle.events) == 2