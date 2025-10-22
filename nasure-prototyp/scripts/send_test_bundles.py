#!/usr/bin/env python3
"""
Send FHIR bundles from examples/ch_elm_bundles to the API.

Usage:
    # Send all bundles once
    python scripts/send_test_bundles.py

    # Send bundles one by one with intervals
    python scripts/send_test_bundles.py --interval 30
"""

import argparse
import json
import time
import os
from pathlib import Path
import requests


def get_api_url():
    """Get API URL from environment variables."""
    host = os.environ.get("API_HOST", "localhost")
    port = 8000
    return f"http://{host}:{port}"


def send_bundle(bundle_data: dict, source_system: str, api_url: str) -> bool:
    """Send a FHIR bundle to the API."""
    payload = {
        "bundle": bundle_data,
        "source_system": source_system
    }

    try:
        response = requests.post(
            f"{api_url}/api/v1/fhir/ingest",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Bundle accepted: {data['bundle_id']}")
            return True
        else:
            print(f"Failed: {response.status_code} - {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False


def health_check(api_url: str) -> bool:
    """Check if the FHIR API is available."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"FHIR API healthy at {api_url}")
            return True
        else:
            print(f"FHIR API unhealthy: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Cannot reach FHIR API at {api_url}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Send FHIR bundles from examples/ch_elm_bundles to the API"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Interval in seconds between bundles (default: 0 - send all at once)"
    )

    parser.add_argument(
        "--source-system",
        type=str,
        default="test-system",
        help="Source system identifier (default: test-system)"
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples" / "ch_elm_bundles"

    api_url = get_api_url()

    print(f"Examples directory: {examples_dir}")
    print(f"API URL: {api_url}\n")

    if not health_check(api_url):
        print("\nAPI not available. Make sure services are running:")
        print("   docker-compose up -d")
        return

    bundle_files = sorted(examples_dir.glob("*.json"))

    if not bundle_files:
        print(f"No JSON files found in {examples_dir}")
        return

    print(f"Found {len(bundle_files)} bundle(s)\n")

    success_count = 0
    for i, bundle_file in enumerate(bundle_files):
        print(f"Sending: {bundle_file.name}")

        try:
            with open(bundle_file, 'r', encoding='utf-8') as f:
                bundle_data = json.load(f)

            if send_bundle(bundle_data, args.source_system, api_url):
                success_count += 1

            if args.interval > 0 and i < len(bundle_files) - 1:
                time.sleep(args.interval)

        except Exception as e:
            print(f"Error loading {bundle_file.name}: {e}")

    print(f"\nSent {success_count}/{len(bundle_files)} bundles successfully")


if __name__ == "__main__":
    main()