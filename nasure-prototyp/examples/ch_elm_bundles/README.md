# CH-ELM Test Data

This directory contains real FHIR bundles from the official CH-ELM Implementation Guide.

## Source

All bundles are downloaded from:
https://build.fhir.org/ig/ahdis/ch-elm/artifacts.html

## Bundles

- **1doc-chlamydia**: Chlamydia trachomatis
- **2doc-gonococcus**: Neisseria gonorrhoeae (Gonococcus)
- **3doc-hepatitisA**: Hepatitis A
- **4doc-hiv**: HIV
- **5doc-campylobacter**: Campylobacter
- **6doc-salmonella**: Salmonella
- **7doc-shigella**: Shigella
- **8doc-neisseria**: Neisseria meningitidis
- **9doc-mpox**: Mpox (Monkeypox)
- **10doc-legionella**: Legionella
- **11doc-malaria**: Malaria

## Usage

Use these bundles for development testing:

```bash
# Send all bundles once
python scripts/send_test_bundles.py

# Send bundles in a loop
python scripts/send_test_bundles.py --loop --interval 30
```

## Regenerating

To re-download the latest versions:

```bash
python scripts/setup_test_data.py
```

## License

These bundles are from the CH-ELM Implementation Guide and are subject to
the licensing terms of that project.
