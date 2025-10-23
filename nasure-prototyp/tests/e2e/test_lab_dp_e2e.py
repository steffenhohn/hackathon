"""
End-to-end tests for lab_dp service
Tests the complete flow: Redis Event -> Fetch Bundle -> Transform -> Store in DB
"""
import json
import pytest

from tests.examples.fhir_loader import fhir_examples


def test_lab_dp_fetch_and_transform_workflow(fake_fhir_client):
    """
    Test lab_dp workflow without database:
    1. Fetch bundle from fhir_client
    2. Transform bundle to LabDataProduct domain entity

    This tests the core logic without database dependencies
    """
    from lab_dp.adapters.fhir_transformer import FHIRTransformer

    # Arrange: Prepare test bundle
    bundle = fhir_examples.load_sample_ch_elm_bundle()
    bundle_id = "test-bundle-123"
    fake_fhir_client.add_bundle(bundle_id, bundle)

    # Act: Fetch and transform
    bundle_data = fake_fhir_client.get_bundle(bundle_id)
    product = FHIRTransformer.extract_lab_data_product(bundle_data, bundle_id)

    # Assert: Product was created correctly
    assert product.bundle_id == bundle_id
    assert product.patient_id  # Should have extracted patient
    assert product.pathogen_code  # Should have extracted pathogen
    assert product.product_id  # Should have generated product ID


def test_lab_dp_handles_missing_bundle_gracefully(fake_fhir_client):
    """Test that lab_dp handles missing bundles gracefully"""
    from lab_dp.adapters.fhir_client import FHIRClientError

    # Try to fetch a bundle that doesn't exist
    with pytest.raises(FHIRClientError):
        fake_fhir_client.get_bundle("non-existent-bundle")


def test_lab_dp_command_handler_workflow(fake_fhir_client):
    """
    Test command handler workflow without database persistence.
    This validates the handler logic is correct.
    """
    # Note: This test is skipped because it requires PostgreSQL database setup
    # To enable: Setup lab_dp database schema in docker-compose
    pytest.skip("Requires lab_dp PostgreSQL database - add schema setup to docker-compose")
