"""Unit tests for FHIR transformer"""
from lab_dp.adapters.fhir_transformer import FHIRTransformer, FHIRTransformationError
import pytest


def test_extract_lab_data_product_from_bundle():
    """Test extracting lab data from a minimal FHIR bundle"""
    bundle = {
        "resourceType": "Bundle",
        "timestamp": "2024-01-15T10:30:00Z",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"value": "patient-123"}]
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {
                        "coding": [{
                            "code": "840539006",
                            "display": "COVID-19"
                        }]
                    },
                    "interpretation": [{
                        "coding": [{"code": "POS"}]
                    }]
                }
            }
        ]
    }

    product = FHIRTransformer.extract_lab_data_product(bundle, "bundle-123")

    assert product.bundle_id == "bundle-123"
    assert product.patient_id == "patient-123"
    assert product.pathogen_code == "840539006"
    assert product.interpretation == "POS"


def test_transform_fails_without_patient():
    """Test transformation fails gracefully without patient data"""
    bundle = {"resourceType": "Bundle", "entry": []}

    with pytest.raises(FHIRTransformationError):
        FHIRTransformer.extract_lab_data_product(bundle, "bundle-123")
