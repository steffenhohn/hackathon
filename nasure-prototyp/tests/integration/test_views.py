"""
Integration tests for views - following Cosmic Python pattern.

Tests verify that:
1. Commands create data products and trigger events
2. Event handlers update the metrics read model
3. Views query the read model correctly
"""
import pytest
from sqlalchemy import text
from lab_dp.adapters.fhir_client import AbstractFHIRClient, FHIRClientError
from lab_dp.domain.commands import CreateDataProduct
from lab_dp.service_layer import messagebus
from lab_dp.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from lab_dp import views


# Minimal test FHIR bundle
MINIMAL_LABORBERICHT_BUNDLE = {
    "resourceType": "Bundle",
    "type": "document",
    "entry": [
        {
            "resource": {
                "resourceType": "Composition",
                "type": {
                    "coding": [{"code": "4241000179101", "display": "Laborbericht"}]
                }
            }
        },
        {
            "resource": {
                "resourceType": "Patient",
                "identifier": [
                    {
                        "system": "urn:oid:2.16.756.5.32",
                        "value": "7562295883070"
                    }
                ]
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "code": {
                    "coding": [{"code": "6349-5", "display": "Gonorrhoe"}]
                },
                "valueCodeableConcept": {
                    "coding": [{"code": "10828004", "display": "Positive"}]
                },
                "effectiveDateTime": "2024-01-15T08:30:00Z"
            }
        }
    ]
}


@pytest.fixture
def simple_fake_fhir_client():
    """Simple fake FHIR client with minimal test data."""
    class SimpleFakeFHIRClient(AbstractFHIRClient):
        def __init__(self):
            self.bundles = {
                "test-bundle-1": MINIMAL_LABORBERICHT_BUNDLE,
                "test-bundle-2": MINIMAL_LABORBERICHT_BUNDLE,
                "test-bundle-3": {
                    **MINIMAL_LABORBERICHT_BUNDLE,
                    "entry": [
                        MINIMAL_LABORBERICHT_BUNDLE["entry"][0],  # Composition
                        MINIMAL_LABORBERICHT_BUNDLE["entry"][1],  # Patient
                        {
                            "resource": {
                                "resourceType": "Observation",
                                "code": {
                                    "coding": [{"code": "6357-8", "display": "Chlamydia"}]
                                },
                                "valueCodeableConcept": {
                                    "coding": [{"code": "10828004", "display": "Positive"}]
                                },
                                "effectiveDateTime": "2024-01-15T09:00:00Z"
                            }
                        }
                    ]
                }
            }

        def get_bundle(self, bundle_id: str) -> dict:
            if bundle_id not in self.bundles:
                raise FHIRClientError(f"Bundle {bundle_id} not found")
            return self.bundles[bundle_id]

    return SimpleFakeFHIRClient()


def test_quality_metrics_view(lab_dp_postgres_session, simple_fake_fhir_client):
    """
    Test quality metrics view shows last_updated and average_delay_hours.

    Following Cosmic Python pattern:
    1. Execute commands via messagebus
    2. Call view function
    3. Assert expected results
    """
    # Act: Execute command to create data product
    uow = SqlAlchemyUnitOfWork(
        session_factory=lambda: lab_dp_postgres_session,
        fhir_client_impl=simple_fake_fhir_client
    )

    cmd = CreateDataProduct(bundle_id="test-bundle-1")
    messagebus.handle(cmd, uow)

    # Assert: Quality metrics view returns expected data
    metrics = views.get_quality_metrics(uow)

    assert metrics["last_updated"] is not None
    assert metrics["average_delay_hours"] is not None
    assert metrics["queried_at"] is not None
    # Average delay should be positive (time since specimen collection)
    assert metrics["average_delay_hours"] >= 0


def test_pathogen_count_last_24h_view(lab_dp_postgres_session, simple_fake_fhir_client):
    """
    Test pathogen count view returns correct count for last 24 hours.

    Following Cosmic Python pattern:
    1. Create multiple data products
    2. Query view for specific pathogen
    3. Verify count is correct
    """
    # Act: Create multiple data products
    uow = SqlAlchemyUnitOfWork(
        session_factory=lambda: lab_dp_postgres_session,
        fhir_client_impl=simple_fake_fhir_client
    )

    # Create two gonorrhea reports and one chlamydia report
    messagebus.handle(CreateDataProduct(bundle_id="test-bundle-1"), uow)
    messagebus.handle(CreateDataProduct(bundle_id="test-bundle-2"), uow)
    messagebus.handle(CreateDataProduct(bundle_id="test-bundle-3"), uow)

    # Assert: Check gonorrhea count (should be 2)
    gonorrhea_metrics = views.get_pathogen_count_last_24h("6349-5", uow)
    assert gonorrhea_metrics["pathogen_code"] == "6349-5"
    assert gonorrhea_metrics["count"] == 2

    # Assert: Check chlamydia count (should be 1)
    chlamydia_metrics = views.get_pathogen_count_last_24h("6357-8", uow)
    assert chlamydia_metrics["pathogen_code"] == "6357-8"
    assert chlamydia_metrics["count"] == 1


def test_view_queries_metrics_read_model(lab_dp_postgres_session, simple_fake_fhir_client):
    """
    Test that views query the metrics read model table.

    Verifies the CQRS pattern: commands update domain, events update read model,
    views query read model.
    """
    # Arrange & Act: Create a data product
    uow = SqlAlchemyUnitOfWork(
        session_factory=lambda: lab_dp_postgres_session,
        fhir_client_impl=simple_fake_fhir_client
    )

    messagebus.handle(CreateDataProduct(bundle_id="test-bundle-1"), uow)

    # Assert: Metrics table should have one entry
    with uow:
        count = uow.session.execute(text("SELECT COUNT(*) FROM metrics")).scalar()
        assert count == 1

        # Verify the entry has expected fields
        row = uow.session.execute(
            text("SELECT product_id, pathogen_code, pathogen_description, created_at FROM metrics")
        ).fetchone()

        assert row[0] is not None  # product_id
        assert row[1] is not None  # pathogen_code
        assert row[2] is not None  # pathogen_description
        assert row[3] is not None  # created_at
