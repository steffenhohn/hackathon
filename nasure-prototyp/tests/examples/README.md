# Test Examples

This directory contains test data examples for FHIR ingestion tests.

## FHIR Bundles (`fhir_bundles/`)

### Files:

- **`sample_ch_elm_bundle.json`** - Complete CH-eLM FHIR bundle with all resources
  - Contains: Composition, Patient, Organization, Observation, Specimen
  - Use for: Full integration testing

- **`minimal_bundle.json`** - Minimal valid FHIR bundle
  - Contains: Only Composition resource
  - Use for: Basic functionality testing

- **`invalid_bundle.json`** - Invalid FHIR bundle for error testing
  - Missing required fields
  - Use for: Error handling tests

## Usage

```python
from tests.examples.fhir_loader import fhir_examples

# Load pre-defined examples
bundle = fhir_examples.load_sample_ch_elm_bundle()
minimal = fhir_examples.load_minimal_bundle()
invalid = fhir_examples.load_invalid_bundle()

# Create variations
custom_bundle = fhir_examples.create_bundle_with_id("sample_ch_elm_bundle.json", "my-custom-id")
multiple_bundles = fhir_examples.create_multiple_bundles("minimal_bundle.json", 5)

# Create large bundles for performance testing
large_bundle = fhir_examples.add_observations_to_bundle(bundle, 20)
```

## Adding New Examples

1. Create new `.json` file in `fhir_bundles/`
2. Follow FHIR R4 structure
3. Add loader method to `fhir_loader.py` if needed
4. Update this README