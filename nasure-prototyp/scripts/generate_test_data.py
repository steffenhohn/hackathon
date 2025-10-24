#!/usr/bin/env python3
"""
Generate and send randomized FHIR bundles to the API.

This script simulates a real-world scenario by:
1. Loading example bundles from examples/ch_elm_bundles/
2. Randomizing patient data, timestamps, and identifiers
3. Sending bundles to the API at regular intervals

Usage:
    # Send 10 bundles with 2 second delay
    python scripts/generate_test_data.py --count 10 --delay 2

    # Continuous mode: send bundles every 5 seconds
    python scripts/generate_test_data.py --continuous --delay 5

    # Send bundles from last 30 days
    python scripts/generate_test_data.py --count 100 --days-min 0 --days-max 30
"""

import argparse
import json
import sys
import time
import random
from pathlib import Path
from typing import List
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from fhir_utils import randomize_bundle


def load_example_bundles(examples_dir: Path = None) -> List[dict]:
    """
    Load all example FHIR bundles from the examples directory.

    Args:
        examples_dir: Path to examples directory

    Returns:
        List of FHIR bundle dictionaries
    """
    if examples_dir is None:
        examples_dir = Path(__file__).parent.parent / "examples" / "ch_elm_bundles"

    bundles = []
    for json_file in examples_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                bundle = json.load(f)
                bundles.append(bundle)
                print(f"✓ Loaded {json_file.name}")
        except Exception as e:
            print(f"✗ Failed to load {json_file.name}: {e}")

    return bundles


def send_bundle_to_api(bundle: dict, api_url: str = "http://localhost:8000") -> dict:
    """
    Send a FHIR bundle to the ingestion API.

    Args:
        bundle: FHIR Bundle dictionary
        api_url: Base URL of the API

    Returns:
        API response as dictionary
    """
    endpoint = f"{api_url}/api/v1/fhir/ingest"

    try:
        response = requests.post(
            endpoint,
            json=bundle,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        raise


def generate_and_send_bundles(
    count: int = 10,
    delay: float = 2.0,
    continuous: bool = False,
    days_min: int = 0,
    days_max: int = 7,
    api_url: str = "http://localhost:8000",
    examples_dir: Path = None
):
    """
    Generate randomized bundles and send them to the API.

    Args:
        count: Number of bundles to send (ignored if continuous=True)
        delay: Delay between sends in seconds
        continuous: If True, run indefinitely
        days_min: Minimum days in the past for timestamps
        days_max: Maximum days in the past for timestamps
        api_url: Base URL of the API
        examples_dir: Path to examples directory
    """
    # Load example bundles
    print("\n" + "=" * 60)
    print("Loading example bundles...")
    print("=" * 60)
    example_bundles = load_example_bundles(examples_dir)

    if not example_bundles:
        print("✗ No example bundles found!")
        sys.exit(1)

    print(f"\n✓ Loaded {len(example_bundles)} example bundle(s)")

    # Send bundles
    print("\n" + "=" * 60)
    print(f"{'Continuous' if continuous else f'Sending {count}'} bundle generation")
    print(f"Delay: {delay}s | Time range: {days_min}-{days_max} days ago")
    print(f"API: {api_url}")
    print("=" * 60 + "\n")

    sent_count = 0
    failed_count = 0

    try:
        while True:
            # Select random example bundle
            original_bundle = random.choice(example_bundles)

            # Randomize the bundle
            randomized_bundle = randomize_bundle(
                original_bundle,
                randomize_time=True,
                days_ago_min=days_min,
                days_ago_max=days_max
            )

            # Send to API
            try:
                response = send_bundle_to_api(randomized_bundle, api_url)
                bundle_id = response.get("bundle_id", "unknown")
                sent_count += 1

                print(f"[{sent_count:4d}] ✓ Sent bundle {bundle_id}")

            except Exception as e:
                failed_count += 1
                print(f"[{sent_count + failed_count:4d}] ✗ Failed to send bundle: {e}")

            # Check if we should stop
            if not continuous and sent_count >= count:
                break

            # Wait before next send
            time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Interrupted by user")

    # Summary
    print("=" * 60)
    print(f"Summary:")
    print(f"  Sent:   {sent_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total:  {sent_count + failed_count}")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate and send randomized FHIR bundles to the API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send 10 bundles with 2 second delay
  %(prog)s --count 10 --delay 2

  # Continuous mode: send bundles every 5 seconds
  %(prog)s --continuous --delay 5

  # Send bundles from last 30 days
  %(prog)s --count 100 --days-min 0 --days-max 30

  # Use custom API URL
  %(prog)s --count 50 --api-url http://api.example.com:8000
        """
    )

    parser.add_argument(
        "-c", "--count",
        type=int,
        default=10,
        help="Number of bundles to send (default: 10, ignored if --continuous)"
    )

    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=2.0,
        help="Delay between sends in seconds (default: 2.0)"
    )

    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously (ignore --count)"
    )

    parser.add_argument(
        "--days-min",
        type=int,
        default=0,
        help="Minimum days in the past for timestamps (default: 0)"
    )

    parser.add_argument(
        "--days-max",
        type=int,
        default=7,
        help="Maximum days in the past for timestamps (default: 7)"
    )

    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )

    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=None,
        help="Path to examples directory (default: ../examples/ch_elm_bundles/)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.days_min < 0 or args.days_max < 0:
        parser.error("days-min and days-max must be >= 0")

    if args.days_min > args.days_max:
        parser.error("days-min cannot be greater than days-max")

    if args.delay < 0:
        parser.error("delay must be >= 0")

    if not args.continuous and args.count <= 0:
        parser.error("count must be > 0 (or use --continuous)")

    # Run the generator
    generate_and_send_bundles(
        count=args.count,
        delay=args.delay,
        continuous=args.continuous,
        days_min=args.days_min,
        days_max=args.days_max,
        api_url=args.api_url,
        examples_dir=args.examples_dir
    )


if __name__ == "__main__":
    main()
