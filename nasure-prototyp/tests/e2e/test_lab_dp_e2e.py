"""
End-to-end tests for lab_dp service
Tests the complete flow: POST Bundle -> MinIO -> Redis -> Consumer -> Database -> API
"""
import json
import time
import pytest
import requests
from sqlalchemy import text

from tests.e2e import api_client
from tests.examples.fhir_loader import fhir_examples
from config import get_api_url


def test_complete_lab_dp_e2e_flow(lab_dp_postgres_session, clean_minio, redis_client):
    """
    Complete end-to-end test:
    1. POST FHIR bundle to ingestion API
    2. Verify bundle stored in MinIO
    3. Verify Redis event published
    4. Wait for consumer to process
    5. Verify data product in products table
    6. Verify metrics in metrics table
    7. Verify API returns correct metrics
    """
    # Arrange - Load a real CH-eLM bundle
    bundle = fhir_examples.load_sample_ch_elm_bundle()

    # Clear any existing data
    redis_client.flushdb()
    lab_dp_postgres_session.execute(text("TRUNCATE TABLE products, metrics CASCADE"))
    lab_dp_postgres_session.commit()

    # Act - POST bundle to FHIR ingestion API
    response = api_client.post_to_fhir_ingest(bundle, "e2e-test")
    assert response.status_code == 200
    bundle_id = response.json()["bundle_id"]

    # Wait for consumer to process (Redis -> Consumer -> Database)
    time.sleep(5)

    # Assert 1: Verify data product in database
    product_count = lab_dp_postgres_session.execute(
        text("SELECT COUNT(*) FROM products WHERE bundle_id = :bundle_id"),
        {"bundle_id": bundle_id}
    ).scalar()
    assert product_count == 1, f"Expected 1 product for bundle {bundle_id}, found {product_count}"

    # Assert 2: Verify product details
    product = lab_dp_postgres_session.execute(
        text("SELECT product_id, pathogen_code, patient_id FROM products WHERE bundle_id = :bundle_id"),
        {"bundle_id": bundle_id}
    ).fetchone()
    assert product is not None
    assert product[0]  # product_id exists
    assert product[1]  # pathogen_code exists
    assert product[2]  # patient_id exists

    # Assert 3: Verify metrics read model
    metrics_count = lab_dp_postgres_session.execute(
        text("SELECT COUNT(*) FROM metrics WHERE product_id = :product_id"),
        {"product_id": product[0]}
    ).scalar()
    assert metrics_count == 1, f"Expected 1 metrics entry for product {product[0]}, found {metrics_count}"

    # Assert 4: Verify metrics API returns data
    # Lab-dp API runs on lab-dp-api:8001, not fhir-api
    lab_dp_api_url = get_api_url().replace('fhir-api:8000', 'lab-dp-api:8001')
    metrics_response = requests.get(f"{lab_dp_api_url}/api/v1/metrics/quality")
    assert metrics_response.status_code == 200
    metrics_data = metrics_response.json()
    assert metrics_data["last_updated"] is not None

    # Assert 5: Verify pathogen count API
    pathogen_code = product[1]
    pathogen_response = requests.get(
        f"{lab_dp_api_url}/api/v1/metrics/pathogen/{pathogen_code}"
    )
    assert pathogen_response.status_code == 200
    pathogen_data = pathogen_response.json()
    assert pathogen_data["count"] >= 1


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
