"""Unit tests for lab_dp domain model"""
from lab_dp.domain.domain import LabDataProduct


def test_lab_data_product_creation():
    """Test basic LabDataProduct creation with events list"""
    product = LabDataProduct(
        product_id="prod-001",
        patient_id="patient-123",
        bundle_id="bundle-456",
        timestamp="2024-01-15T10:30:00Z",
        pathogen_code="840539006",
        pathogen_description="COVID-19",
        interpretation="POS"
    )

    assert product.product_id == "prod-001"
    assert product.bundle_id == "bundle-456"
    assert len(product.events) == 0
