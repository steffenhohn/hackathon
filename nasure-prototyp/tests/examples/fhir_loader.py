"""Utility for loading FHIR test examples from JSON files"""
import json
import copy
from pathlib import Path
from typing import Dict, Any


class FHIRExampleLoader:
    """Loads FHIR bundle examples from JSON files"""

    def __init__(self):
        self.examples_dir = Path(__file__).parent / "fhir_bundles"

    def load_example(self, filename: str) -> Dict[str, Any]:
        """Load FHIR bundle example from JSON file"""
        filepath = self.examples_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"FHIR example not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_sample_ch_elm_bundle(self) -> Dict[str, Any]:
        """Load the main CH-eLM sample bundle"""
        return self.load_example("sample_ch_elm_bundle.json")

    def load_minimal_bundle(self) -> Dict[str, Any]:
        """Load minimal test bundle"""
        return self.load_example("minimal_bundle.json")

    def load_invalid_bundle(self) -> Dict[str, Any]:
        """Load invalid bundle for error testing"""
        return self.load_example("invalid_bundle.json")

    def create_bundle_with_id(self, base_filename: str, new_id: str) -> Dict[str, Any]:
        """Create a bundle with a specific ID based on existing example"""
        bundle = copy.deepcopy(self.load_example(base_filename))
        bundle["id"] = new_id
        if "identifier" in bundle:
            bundle["identifier"]["value"] = new_id
        return bundle

    def create_multiple_bundles(self, base_filename: str, count: int, id_prefix: str = "test-bundle") -> list:
        """Create multiple bundles with different IDs"""
        bundles = []
        for i in range(count):
            bundle_id = f"{id_prefix}-{i+1:03d}"
            bundle = self.create_bundle_with_id(base_filename, bundle_id)
            bundles.append(bundle)
        return bundles

    def add_observations_to_bundle(self, bundle: Dict[str, Any], count: int) -> Dict[str, Any]:
        """Add additional observations to a bundle for large bundle testing"""
        bundle = copy.deepcopy(bundle)

        for i in range(count):
            obs = {
                "resource": {
                    "resourceType": "Observation",
                    "id": f"obs-{i+2:03d}",
                    "status": "final",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "94500-6",
                                "display": "SARS-CoV-2 RNA detected"
                            }
                        ]
                    },
                    "subject": {
                        "reference": "Patient/patient-001"
                    },
                    "effectiveDateTime": f"2024-01-15T{9+i:02d}:00:00Z",
                    "valueCodeableConcept": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "260415000",
                                "display": "Not detected"
                            }
                        ]
                    }
                }
            }
            bundle["entry"].append(obs)

        return bundle


# Global instance for easy import
fhir_examples = FHIRExampleLoader()