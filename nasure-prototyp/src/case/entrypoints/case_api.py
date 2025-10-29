"""
Case API Entrypoint - Thin API with Command Dispatch
"""
from typing import Dict, Any, List
from sqlalchemy import create_engine
from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import logging
import config
from datetime import datetime, timezone
from case.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from case.adapters import orm
from case.domain import commands
from case.service_layer import handlers,messagebus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This sends logs to stdout/stderr
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Case Mgmt API",
    description="Case management service",
    version="1.0.0"
)

# Initialize database and ORM mappers (Cosmic Python pattern)
@app.on_event("startup")
async def startup_event():
    engine = create_engine(config.get_postgres_uri())
    orm.metadata.create_all(engine)
    orm.start_mappers()
    logger.info("✓ Case Databases initialized")

# ---------- Request/Response models ----------

class CaseResponse(BaseModel):
    case_id: str
    patient_id: str
    pathogen_code: str
    pathogen_description: str
    lab_timestamp: datetime
    created_at: datetime
    case_class: str  
    status: str
    canton: str

class PaginatedCasesResponse(BaseModel):
    cases: List[CaseResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

class CreateCaseRequest(BaseModel):
    product_id: str
    patient_id: str
    pathogen_code: str
    pathogen_description: str
    lab_timestamp: datetime     # Lab report timestamp (from FHIR bundle)
    canton: str                 # 2-letter canton code

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "0760c467-25b9-42d3-87b1-5658c02e5a9b",
                "patient_id": "123e4567-e89b-12d3-a456-426614174000",
                "pathogen_code": "32781-7",
                "pathogen_description": "Legionella pneumophila [Presence] in Specimen by Organism specific culture",
                "lab_timestamp": "2024-10-24T10:30:00Z",              
                "canton": "BE"
            }
        }
    }

class CaseCreatedResponse(BaseModel):
    case: CaseResponse  # Details of the created or updated case
    created: bool       # Was case newly created or existing one updated

class ProductLink(BaseModel):
    """Model for a product link"""
    product_id: str
    is_original: bool
    linked_at: Optional[datetime] = None 

class ProductLinksResponse(BaseModel):
    case_id: str
    products: List[ProductLink]  
    total_count: int

class ProductLinkRequest(BaseModel):
    case_id: str
    product_id: str
    is_original: bool = False

# ---------- Endpoints ----------

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "case-mgmt-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/cases", response_model=PaginatedCasesResponse, summary="Get cases with pagination and filtering")
def get_all_cases(
    page_size: int = Query(20, ge=1, le=100, description="Number of cases per page"),
    page: int = Query(1, ge=1, description="Page offset (starting from 1)"),
    status: Optional[str] = Query("not_closed", description="Filter by case status. Use 'all' for no filter"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    pathogen_code: Optional[str] = Query(None, description="Filter by pathogen code"),
    canton: Optional[str] = Query(None, description="Filter by canton"),
):
    """
    Retrieve all cases with pagination and optional filtering.
    
    Args:
        page_size: Number of cases per page (max 100)
        page: Page offset (starting from 1)
        status: Filter by case status. Default: 'not_closed' (excludes 'closed', 'archived'), use 'all' for no filter
        patient_id: Filter by patient ID (optional)
        pathogen_code: Filter by pathogen code (optional)
        canton: Filter by canton (optional)     
        
    Returns:
        Paginated list of cases with metadata
    """
    try:
        logger.info(f"Fetching cases: page={page}, page_size={page_size}, case status={status}")
        
        with SqlAlchemyUnitOfWork() as uow:
            # Get cases from repository with filters and pagination
            cases, total_count = uow.cases.get_all_cases_paginated(
                page_size=page_size,
                page=page,
                status_filter=status,
                patient_id_filter=patient_id,
                pathogen_code_filter=pathogen_code,
                canton_filter=canton
            )
            
            # Convert to response format
            case_responses = [
                CaseResponse(
                    case_id=case.case_id,
                    patient_id=case.patient_id,
                    pathogen_code=case.pathogen_code,
                    pathogen_description=case.pathogen_description,
                    lab_timestamp=case.lab_timestamp,
                    created_at=case.created_at,
                    case_class=case.case_class,
                    status=case.status,
                    canton=case.canton
                )
                for case in cases
            ]
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
            has_next = page < total_pages
            has_previous = page > 1
            
            return PaginatedCasesResponse(
                cases=case_responses,
                total_count=total_count,
                page_size=page_size,
                page=page,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous
            )
            
    except Exception as e:
        logger.error(f"Error retrieving cases: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/cases/{case_id}", response_model=CaseResponse, summary="Get case by case_id")
def get_case_by_id(case_id: str):
    """
    Get a specific case by its case_id.
    
    Args:
        case_id: The unique case identifier
        
    Returns:
        Complete case details
    """
    try:
        logger.info(f"Retrieving case with ID: {case_id}")
        
        with SqlAlchemyUnitOfWork() as uow:
            # Get case from repository
            case = uow.cases.get(case_id)
            
            if not case:
                raise HTTPException(status_code=404, detail=f"Case with ID {case_id} not found")
            
            # Convert to response format
            return CaseResponse(
                case_id=case.case_id,
                patient_id=case.patient_id,
                pathogen_code=case.pathogen_code,
                pathogen_description=case.pathogen_description,
                lab_timestamp=case.lab_timestamp,
                created_at=case.created_at,
                case_class=case.case_class,
                status=case.status,
                canton=case.canton
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/cases", response_model=CaseCreatedResponse, summary="Create new or upsert existing case based on report data")
def create_case(case_request: CreateCaseRequest):
    """
    Create a new case record.
    
    Args:
        case_request: Case data including patient_id, case details, pathogen, etc.
        
    Returns:
        Created case and information whether it was newly created or updated
    """
    try:
        logger.info(f"Creating new case for patient {case_request.patient_id}")
        
        # Create command
        lab_timestamp = case_request.lab_timestamp
        if lab_timestamp.tzinfo is None:
            # If naive datetime, assume it's UTC
            lab_timestamp = lab_timestamp.replace(tzinfo=timezone.utc)
        
        cmd = commands.CreateCaseFromDataProduct(
            product_id=case_request.product_id,
            patient_id=case_request.patient_id,
            pathogen_code=case_request.pathogen_code,
            pathogen_description=case_request.pathogen_description,
            lab_timestamp=lab_timestamp,
            stored_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        
        # Delegate to message bus
        with SqlAlchemyUnitOfWork() as uow:
            results = messagebus.handle(cmd, uow)

            if not results or len(results) == 0:
                raise ValueError("Handler did not return expected results")

            result = results[0]
            if isinstance(result, tuple) and len(result) == 2:
                case_id, created = result

            else:
                raise ValueError("Handler returned unexpected format")

            # Retrieve the case to return full details
            case = uow.cases.get(case_id)
            if not case:
                raise ValueError(f"Case with ID {case_id} not found after creation")

            # Convert to response format
            case_response = CaseResponse(
                case_id=case.case_id,
                patient_id=case.patient_id,
                pathogen_code=case.pathogen_code,
                pathogen_description=case.pathogen_description,
                lab_timestamp=case.lab_timestamp,
                created_at=case.created_at,
                case_class=case.case_class,
                status=case.status,
                canton=case.canton
            )
            
            return CaseCreatedResponse(
                case=case_response,
                created=created
            )

    except ValueError as e:
        logger.error(f"Validation error creating case: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@app.get("/api/v1/cases/{case_id}/products", response_model=ProductLinksResponse, summary="Get all products linked to a specific case")
def get_case_products(case_id: str):
    """Get all products linked to a specific case"""
    try:
        
        with SqlAlchemyUnitOfWork() as uow:
            # Get cases from repository with filters and pagination
            products = uow.case_products.get_products_for_case(
                case_id=case_id
            )
            # Convert to response format
            product_links = [
                {"product_id": product.product_id, "is_original": product.is_original, "linked_at": product.linked_at}
                for product in products
            ]

            return ProductLinksResponse(
                case_id=case_id,
                products=product_links,
                total_count=len(product_links)
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching case products for case_id: {case_id}: {str(e)}")

@app.post("/api/v1/cases/{case_id}/products", summary="Link a product to an existing case")
async def link_product_to_case(product_link: ProductLinkRequest):
    """Link a product to an existing case"""
    try:
        
        with SqlAlchemyUnitOfWork() as uow:

            case_product = uow.case_products.link_product_to_case(
                case_id=product_link.case_id,
                product_id=product_link.product_id,
                is_original=product_link.is_original    
            )

            if case_product:
                return {
                    "message": "Product linked successfully to case",
                    "case_id": product_link.case_id,
                    "product_id": product_link.product_id,
                    "is_original": product_link.is_original
            }

            else:
                raise HTTPException(status_code=400, detail="Failed to link product to case")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error linking product: {str(e)}")