import logging
from sqlalchemy import text
import httpx


from case.domain.commands import CreateCaseFromDataProduct
from case.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


def create_case_from_data_product(
    command: CreateCaseFromDataProduct,
    uow: AbstractUnitOfWork
) -> str:
    """
    Create case from new data product (lab or clinical report).

    
       Schritte:
    - Wir suchen in 'falldatenprodukt' nach einem vorhandenen Fall (case_ID),
      der dieselbe Patient_ID + Pathogen_code hat und dessen Fall-Datum innerhalb
      von case_duration_days um incoming.Date liegt.
    - Wenn gefunden: wir nehmen dessen case_ID.
      Wenn mehrere passen, nehmen wir den mit dem 'nächstliegenden' Datum (kleinste Differenz).
    - Wenn nicht gefunden: wir erzeugen einen neuen Eintrag in 'falldatenprodukt'
      mit neuer case_ID.
    - In beiden Fällen tragen wir (ID, case_ID) in Fall_meldung_tabelle ein
      (aber nur, falls dieses Paar noch nicht existiert).
    - Die Funktion gibt die verwendete case_ID zurück.
    

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
                raise ValueError(f"Data product {command.product_id} not found in lab_dp")  

            logger.info(f"Fetched data product from lab_dp: {product}")

            # Step 2: fetch all cases for this patient and patogen
            existing_cases = uow.cases.get_cases_by_patient_and_pathogen(
                command.patient_id, 
                command.pathogen_code
            )
            
            logger.info(f"Found {len(existing_cases)} existing cases for patient {command.patient_id} and pathogen {command.pathogen_code}")
            
            # Step 3: Find or create case
            case_id = find_or_create_case(existing_cases, product, command, uow)

            # Commit transaction
            uow.commit()

            #TODO chech if new case was created or existing one updated 
            logger.info(f"Committed case {case_id} to database")

        logger.info(f"Successfully created/updated case {case_id} from product {command.product_id}")
        return case_id

    except Exception as e:
        logger.error(f"Unexpected error processing product {command.product_id}: {e}")
        raise

def find_or_create_case(existing_cases: list, product: dict, command: CreateCaseFromDataProduct, uow: AbstractUnitOfWork) -> str:
    """Find existing case within duration or create new one."""
    from datetime import datetime, timedelta
    
    CASE_DURATION_DAYS = 28 # days window to match existing cases
    
    # Parse incoming date
    #TODO: timestamp should be changed to collection date of lab sample
    incoming_date = datetime.fromisoformat(command.timestamp.replace('Z', '+00:00'))
    
    # Filter cases within duration window
    matching_cases = []
    for case in existing_cases:
        case_date = datetime.fromisoformat(case.case_date)
        date_diff = abs((incoming_date - case_date).days)
        
        if date_diff <= CASE_DURATION_DAYS:
            matching_cases.append({
                "case": case,
                "date_diff": date_diff
            })
    
    if matching_cases:
        # Find case with smallest date difference
        closest_case = min(matching_cases, key=lambda x: x["date_diff"])
        case_id = closest_case["case"].case_id
        
        logger.info(f"Reusing existing case {case_id} (date diff: {closest_case['date_diff']} days)")
        return case_id
    else:
        # Create new case internally
        case_id = create_new_case_internal(product, command, uow)
        logger.info(f"Created new case {case_id}")
        return case_id

def create_new_case_internal(product: dict, command: CreateCaseFromDataProduct, uow: AbstractUnitOfWork) -> str:
    """Create a new case using internal repository."""
    from uuid import uuid4
    from case.domain.domain import CaseRecord
    
    case_id = str(uuid4())
    
    new_case = CaseRecord(
        case_id=case_id,
        patient_id=command.patient_id,
        case_date=command.timestamp,
        case_class="sicherer Fall",
        case_status="neu", 
        pathogen=command.pathogen_description,
        canton=product.get("canton", "na")
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

def extract_case_data_from_product(product_data: dict, command: CreateCaseFromDataProduct) -> dict:
    """Extract case-relevant information from product data."""
    return {
        "patient_id": command.patient_id,
        "pathogen_code": command.pathogen_code,
        "pathogen_description": command.pathogen_description,
        "case_date": command.timestamp or product_data.get("timestamp"),
        "case_class": "confirmed",  # or derive from product data
        "case_status": "active",
        "canton": product_data.get("canton", "ZH"),  # extract from product
        "product_id": command.product_id
    }