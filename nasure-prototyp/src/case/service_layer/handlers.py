import logging
from sqlalchemy import text
import httpx
from typing import Tuple
from case.domain.domain import CaseRecord
from case.domain.commands import CreateCaseFromDataProduct
from case.service_layer.unit_of_work import AbstractUnitOfWork
from uuid import uuid4
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def create_case_from_data_product(command: CreateCaseFromDataProduct, uow: AbstractUnitOfWork) -> Tuple[str,bool]:
    """
    Create case from new data product (lab or clinical report).

    Steps:
    1. Search in 'falldatenprodukt' for an existing case (case_ID) with the same
       Patient_ID + Pathogen_code and case date within case_duration_days of incoming date.
    2. If found: use its case_ID. If multiple, pick the one with the smallest date difference.
    3. If not found: create a new entry in 'falldatenprodukt' with a new case_ID.
    4. In both cases, insert (ID, case_ID) into Fall_meldung_tabelle if this pair does not exist yet.
    5. Return the used case_ID.

    Args:
        command: CreateCase command with product_id
        uow: Unit of work for transaction management

    Returns:
        case_id: The ID of the created case
    """
    logger.info(f"Processing CreateCaseFromDataProduct command for product {command.product_id}")

    try:
        
        with uow:
            # Step 1: Fetch newly created DataProduct depending on product_type
            # TODO: Support clinical reports later
            product = fetch_product_from_lab_dp(command.product_id)
            if not product:
                logger.error(f"Data product {command.product_id} not found in lab_dp")
                product={}

            logger.info(f"Fetched data product from lab_dp: {product}")

            # Step 2: fetch all cases for this patient and patogen
            existing_cases, total = uow.cases.get_all_cases_paginated(
                page_size=100,
                page=1,
                patient_id_filter=command.patient_id,
                pathogen_code_filter=command.pathogen_code,
            )

            logger.info(f"Found {total} existing cases for patient {command.patient_id} and pathogen {command.pathogen_code}")
            if total > 100:
                logger.warning(f"More than 100 existing cases found for patient {command.patient_id} and pathogen {command.pathogen_code}. Only first 100 will be considered.")
                # TODO: Implement pagination if needed
            
            # Step 3: Find or create case
            case_id, created = find_or_create_case(existing_cases, product, command, uow)

            # Commit transaction
            uow.commit()

            #TODO chech if new case was created or existing one updated 
            if created:
                logger.info(f"Successfully created new case {case_id} from product {command.product_id}")
            else:
                logger.info (f"Updated existing case {case_id} with product {command.product_id}")

        return case_id, created

    except Exception as e:
        logger.error(f"Unexpected error processing product {command.product_id}: {e}")
        raise

def find_or_create_case(existing_cases: list, product: dict, command: CreateCaseFromDataProduct, uow: AbstractUnitOfWork) -> Tuple[str,bool]:
    """
    Find existing case within duration or create new one.
    
    Returns: (case_id, created)
    """
   
    CASE_DURATION_DAYS = 28 # days window to match existing cases
    
    # Filter cases within duration window
    matching_cases = []
    for case in existing_cases:
        # Normalize case timestamp
        case_lab_timestamp = to_utc(case.lab_timestamp)
        date_diff = abs((command.lab_timestamp - case_lab_timestamp).days)
        
        if date_diff <= CASE_DURATION_DAYS:
            matching_cases.append({
                "case": case,
                "date_diff": date_diff
            })
    
    if matching_cases:
        # Find case with smallest date difference
        closest_match = min(matching_cases, key=lambda x: x["date_diff"])
        closest_case = closest_match["case"]
            
        logger.info(f"Reusing existing case {closest_case.case_id} (date diff: {closest_match['date_diff']} days)")
        return closest_case.case_id, False
    else:
        # Create new case internally
        new_case_id = create_new_case_internal(product, command, uow)
        logger.info(f"Created new case {new_case_id}")
        return new_case_id, True

def create_new_case_internal(product: dict, command: CreateCaseFromDataProduct, uow: AbstractUnitOfWork) -> str:
    """
    Create a new case using internal repository.
    
    Returns: case_id
    """
        
    case_id = str(uuid4())
    
    new_case = CaseRecord(
        case_id=case_id,
        patient_id=command.patient_id,
        pathogen_code=command.pathogen_code,
        pathogen_description=command.pathogen_description,
        lab_timestamp=command.lab_timestamp,
        created_at=datetime.now(timezone.utc),
        case_class="sicherer Fall",
        status="neu", 
        canton=product.get("canton", "ZH"),  # default to ZH if not provided
    )

    # Add to repository
    uow.cases.add(new_case)
    
    return case_id

def publish_case_created_event(event, uow: AbstractUnitOfWork):
    """
    Publish CaseCreated event to external systems.

    Following Cosmic Python pattern: publish domain events to Redis
    for consumption by external services (e.g., alerting, dashboards).

    Args:
        event: CaseCreated event
        uow: Unit of work
    """
    logger.info(f"Publishing CaseCreated event for case {event.case_id}")
    try:
        # Import here to avoid circular dependency
        from lab_dp.adapters import redis_adapter

        redis_adapter.publish("surveillance:cases", event)
        logger.info(f"Published CaseCreated event for {event.case_id}")

    except Exception as e:
        logger.error(f"Failed to publish CaseCreated event for {event.case_id}: {e}")
        # Don't re-raise - external failures shouldn't break the flow

from typing import Optional

def fetch_product_from_lab_dp(product_id: str) -> Optional[dict]:
    """Fetch product data from lab_dp API."""
    try:
        # Use environment variable for lab_dp URL
        import os
        lab_dp_url = os.getenv("LAB_DP_URL", "http://lab-dp-api:8001")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{lab_dp_url}/api/v1/data-product/{product_id}")
            
            if response.status_code == 404:
                logger.error(f"Product {product_id} not found in lab_dp")
                return None
                
            response.raise_for_status()
            return response.json()
            
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to lab_dp API: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from lab_dp API: {e}")
        raise

def to_utc(dt):
    """Ensure a datetime is timezone-aware and in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# def extract_case_data_from_product(product_data: dict, command: CreateCaseFromDataProduct) -> dict:
#     """Extract case-relevant information from product data."""
#     return {
#         "patient_id": command.patient_id,
#         "pathogen_code": command.pathogen_code,
#         "pathogen_description": command.pathogen_description,
#         "case_date": command.timestamp or product_data.get("timestamp"),
#         "case_class": "confirmed",  # or derive from product data
#         "case_status": "active",
#         "canton": product_data.get("canton", "ZH"),  # extract from product
#         "product_id": command.product_id
#     }