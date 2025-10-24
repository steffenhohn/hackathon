"""
Utility functions for FHIR bundle manipulation and randomization.
Used for generating test data and simulating real-world scenarios.
"""

import copy
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from faker import Faker

# Initialize Faker with Swiss locale for realistic data
fake = Faker(['de_CH', 'fr_CH', 'it_CH'])


def randomize_patient_data(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace patient information with random data using Faker.

    Args:
        bundle: FHIR Bundle dictionary

    Returns:
        Modified bundle with randomized patient data
    """
    bundle = copy.deepcopy(bundle)

    # Generate random patient data
    gender = random.choice(['male', 'female'])
    first_name = fake.first_name_male() if gender == 'male' else fake.first_name_female()
    last_name = fake.last_name()
    birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat()

    # Swiss AHV number format (13 digits)
    ahv_number = f"756{fake.random_number(digits=10, fix_len=True)}"

    # Address
    street = fake.street_name()
    street_number = fake.building_number()
    city = fake.city()
    postal_code = fake.postcode()
    canton = random.choice(['ZH', 'BE', 'LU', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG', 'FR', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'SG', 'GR', 'AG', 'TG', 'TI', 'VD', 'VS', 'NE', 'GE', 'JU'])

    # Replace patient data in bundle
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") == "Patient":
            # Update identifier (AHV number)
            if "identifier" in resource and resource["identifier"]:
                resource["identifier"][0]["value"] = ahv_number

            # Update name
            if "name" in resource and resource["name"]:
                resource["name"][0]["family"] = last_name
                resource["name"][0]["given"] = [first_name]

            # Update gender and birth date
            resource["gender"] = gender
            resource["birthDate"] = birth_date

            # Update address
            if "address" in resource and resource["address"]:
                address = resource["address"][0]
                address["line"] = [f"{street} {street_number}"]
                address["city"] = city
                address["postalCode"] = postal_code
                address["state"] = canton

    return bundle


def randomize_timestamps(bundle: Dict[str, Any],
                        days_ago_min: int = 0,
                        days_ago_max: int = 7) -> Dict[str, Any]:
    """
    Randomize timestamps in the bundle to simulate reports from the past.

    Args:
        bundle: FHIR Bundle dictionary
        days_ago_min: Minimum days in the past
        days_ago_max: Maximum days in the past

    Returns:
        Modified bundle with randomized timestamps
    """
    bundle = copy.deepcopy(bundle)

    # Generate a random timestamp in the past
    days_ago = random.uniform(days_ago_min, days_ago_max)
    random_time = datetime.now() - timedelta(days=days_ago)
    timestamp_str = random_time.isoformat()

    # Update bundle timestamp
    if "timestamp" in bundle:
        bundle["timestamp"] = timestamp_str

    # Update resource timestamps
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        if resource_type == "Composition":
            if "date" in resource:
                resource["date"] = timestamp_str

        elif resource_type == "Observation":
            if "effectiveDateTime" in resource:
                # Observation time slightly before report time
                observation_time = random_time - timedelta(hours=random.uniform(1, 48))
                resource["effectiveDateTime"] = observation_time.isoformat()

        elif resource_type == "Specimen":
            if "collection" in resource and "collectedDateTime" in resource["collection"]:
                # Collection time even earlier
                collection_time = random_time - timedelta(days=random.uniform(2, 5))
                resource["collection"]["collectedDateTime"] = collection_time.date().isoformat()

    return bundle


def randomize_identifiers(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Randomize all UUIDs and identifiers in the bundle.

    Args:
        bundle: FHIR Bundle dictionary

    Returns:
        Modified bundle with new UUIDs
    """
    bundle = copy.deepcopy(bundle)

    # Generate new bundle ID
    new_bundle_id = str(uuid.uuid4())
    if "id" in bundle:
        bundle["id"] = f"Bundle-{new_bundle_id}"

    if "identifier" in bundle and "value" in bundle["identifier"]:
        bundle["identifier"]["value"] = f"urn:uuid:{new_bundle_id}"

    # Map old UUIDs to new ones for references
    uuid_map = {}

    # First pass: generate new UUIDs for all resources
    for entry in bundle.get("entry", []):
        old_url = entry.get("fullUrl", "")
        if "urn:uuid:" in old_url:
            old_uuid = old_url.replace("urn:uuid:", "")
            new_uuid = str(uuid.uuid4())
            uuid_map[old_uuid] = new_uuid
            entry["fullUrl"] = f"urn:uuid:{new_uuid}"

        resource = entry.get("resource", {})
        if "id" in resource:
            old_id = resource["id"]
            new_id = str(uuid.uuid4())
            uuid_map[old_id] = new_id
            resource["id"] = new_id

        # Update Composition identifier
        if resource.get("resourceType") == "Composition":
            if "identifier" in resource and "value" in resource["identifier"]:
                resource["identifier"]["value"] = f"urn:uuid:{new_bundle_id}"

    # Second pass: update all references
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        _replace_references_recursive(resource, uuid_map)

    return bundle


def _replace_references_recursive(obj: Any, uuid_map: Dict[str, str]) -> None:
    """Helper function to recursively replace UUID references."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "reference" and isinstance(value, str):
                # Replace UUID references
                for old_uuid, new_uuid in uuid_map.items():
                    if old_uuid in value:
                        obj[key] = value.replace(old_uuid, new_uuid)
            else:
                _replace_references_recursive(value, uuid_map)
    elif isinstance(obj, list):
        for item in obj:
            _replace_references_recursive(item, uuid_map)


def randomize_organization_data(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Randomize organization (lab, hospital) data.

    Args:
        bundle: FHIR Bundle dictionary

    Returns:
        Modified bundle with randomized organization data
    """
    bundle = copy.deepcopy(bundle)

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") == "Organization":
            # Generate random organization name
            org_type = random.choice(['laboratory', 'hospital', 'clinic'])

            if org_type == 'laboratory':
                org_name = f"{fake.company()} Labor AG"
            elif org_type == 'hospital':
                org_name = f"Kantonsspital {fake.city()}"
            else:
                org_name = f"Klinik {fake.last_name()}"

            resource["name"] = org_name

            # Update GLN (Global Location Number - Swiss healthcare identifier)
            if "identifier" in resource and resource["identifier"]:
                resource["identifier"][0]["value"] = f"760{fake.random_number(digits=10, fix_len=True)}"

    return bundle


def randomize_practitioner_data(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Randomize practitioner (doctor) data.

    Args:
        bundle: FHIR Bundle dictionary

    Returns:
        Modified bundle with randomized practitioner data
    """
    bundle = copy.deepcopy(bundle)

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") == "Practitioner":
            # Generate random practitioner
            gender = random.choice(['male', 'female'])
            first_name = fake.first_name_male() if gender == 'male' else fake.first_name_female()
            last_name = fake.last_name()

            if "name" in resource and resource["name"]:
                resource["name"][0]["family"] = last_name
                resource["name"][0]["given"] = [first_name]

            # Update GLN
            if "identifier" in resource and resource["identifier"]:
                resource["identifier"][0]["value"] = f"760{fake.random_number(digits=10, fix_len=True)}"

            # Update contact info
            if "telecom" in resource:
                for contact in resource["telecom"]:
                    if contact.get("system") == "phone":
                        contact["value"] = f"+41 {fake.random_number(digits=2, fix_len=True)} {fake.random_number(digits=3, fix_len=True)} {fake.random_number(digits=2, fix_len=True)} {fake.random_number(digits=2, fix_len=True)}"
                    elif contact.get("system") == "email":
                        contact["value"] = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"

    return bundle


def randomize_bundle(bundle: Dict[str, Any],
                    randomize_time: bool = True,
                    days_ago_min: int = 0,
                    days_ago_max: int = 7) -> Dict[str, Any]:
    """
    Fully randomize a FHIR bundle for testing.

    Applies all randomization functions to create realistic test data.

    Args:
        bundle: Original FHIR Bundle dictionary
        randomize_time: Whether to randomize timestamps
        days_ago_min: Minimum days in the past for timestamps
        days_ago_max: Maximum days in the past for timestamps

    Returns:
        Fully randomized bundle
    """
    bundle = copy.deepcopy(bundle)

    # Apply all randomization functions
    bundle = randomize_identifiers(bundle)
    bundle = randomize_patient_data(bundle)
    bundle = randomize_organization_data(bundle)
    bundle = randomize_practitioner_data(bundle)

    if randomize_time:
        bundle = randomize_timestamps(bundle, days_ago_min, days_ago_max)

    return bundle
