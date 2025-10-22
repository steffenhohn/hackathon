#!/usr/bin/env python3
"""
Setup script to download CH-ELM FHIR bundles from the official Implementation Guide.

Downloads bundles from https://build.fhir.org/ig/ahdis/ch-elm/artifacts.html
and saves them to examples/ch_elm_bundles for testing.

Usage:
    python scripts/setup_test_data.py
"""

import json
import requests
from pathlib import Path


# CH-ELM bundle URLs from the official IG
BUNDLE_URLS = {
    "anthrax_1": "https://build.fhir.org/ig/ahdis/ch-elm/Bundle-38Doc-Anthrax.json",
    "legionella_1": "https://build.fhir.org/ig/ahdis/ch-elm/Bundle-10Doc-Legionella.json",
    "malaria_1": "https://build.fhir.org/ig/ahdis/ch-elm/Bundle-11Doc-Malaria.json",
}


def download_bundle(url: str, name: str, output_dir: Path) -> bool:
    """Download a FHIR bundle from the IG."""
    try:
        print(f"Downloading {name}...", end=" ")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        bundle_data = response.json()

        output_file = output_dir / f"{name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_data, f, indent=2, ensure_ascii=False)

        print(f"Saved to {output_file.name}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples" / "ch_elm_bundles"

    examples_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading CH-ELM bundles to: {examples_dir}\n")

    success_count = 0
    for name, url in BUNDLE_URLS.items():
        if download_bundle(url, name, examples_dir):
            success_count += 1

    print(f"\nDownloaded {success_count}/{len(BUNDLE_URLS)} bundles successfully")

    if success_count == len(BUNDLE_URLS):
        print(f"Setup complete! Bundles saved to {examples_dir}")
    else:
        print(f"Some bundles failed to download ({success_count}/{len(BUNDLE_URLS)})")


if __name__ == "__main__":
    main()