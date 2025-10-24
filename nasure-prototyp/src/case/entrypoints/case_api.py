"""
Case API Entrypoint - Thin API with Command Dispatch
"""
import config
from typing import Dict, Any, List
from sqlalchemy import create_engine
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, RootModel
import logging
import os
from datetime import datetime, timezone
from case.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from case.adapters import orm

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

class ResolveRequest(BaseModel):
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str   # YYYY-MM-DD
    canton: str

class ResolveResponse(BaseModel):
    case_id: str

class PatientDetailsResponse(BaseModel):
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str
    canton: str


# Add this response model with your other models
class CaseResponse(BaseModel):
    case_id: str
    patient_id: str
    case_date: str
    case_class: str  
    case_status: str
    pathogen: str
    canton: str

class CasesListResponse(BaseModel):
    cases: List[CaseResponse]
    total_count: int

# Add this request model with your other models
class CreateCaseRequest(BaseModel):
    patient_id: str
    case_date: str           # YYYY-MM-DD format
    case_class: str          # e.g., "confirmed", "suspected", "probable"
    case_status: str         # e.g., "active", "recovered", "deceased"
    pathogen: str            # e.g., "COVID-19", "Influenza A", etc.
    canton: str              # 2-letter canton code
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_id": "123e4567-e89b-12d3-a456-426614174000",
                "case_date": "2024-10-24",
                "case_class": "confirmed", 
                "case_status": "active",
                "pathogen": "COVID-19",
                "canton": "ZH"
            }
        }
    }

class CreateCaseResponse(BaseModel):
    case_id: str
    patient_id: str
    case_date: str
    case_class: str
    case_status: str
    pathogen: str
    canton: str
    created: bool


# ---------- Endpoints ----------

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "case-mgmt-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

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
                case_date=case.case_date,
                case_class=case.case_class,
                case_status=case.case_status,
                pathogen=case.pathogen,
                canton=case.canton
            )
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/cases/patient/{patient_id}/pathogen/{pathogen}", response_model=CasesListResponse, summary="Get cases by patient and pathogen")
def get_cases_by_patient_and_pathogen(patient_id: str, pathogen: str):
    """
    Get all cases for a specific patient and pathogen.
    
    Args:
        patient_id: The patient's unique identifier
        pathogen: The pathogen code to filter by
        
    Returns:
        List of cases matching the patient and pathogen criteria
    """
    try:
        with SqlAlchemyUnitOfWork() as uow:
            # Get cases from repository
            cases = uow.cases.get_cases_by_patient_and_pathogen(patient_id, pathogen)
            
            if not cases:
                return CasesListResponse(cases=[], total_count=0)
            
            # Convert to response format
            case_responses = [
                CaseResponse(
                    case_id=case.case_id,
                    patient_id=case.patient_id,
                    case_date=case.case_date,
                    case_class=case.case_class,
                    case_status=case.case_status,
                    pathogen=case.pathogen,
                    canton=case.canton
                )
                for case in cases
            ]
            
            return CasesListResponse(
                cases=case_responses,
                total_count=len(case_responses)
            )
            
    except Exception as e:
        logger.error(f"Error retrieving cases for patient {patient_id} and pathogen {pathogen}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/cases", response_model=CreateCaseResponse, summary="Create a new case")
def create_case(case_request: CreateCaseRequest):
    """
    Create a new case record.
    
    Args:
        case_request: Case data including patient_id, case details, pathogen, etc.
        
    Returns:
        Created case with generated case_id
    """
    try:
        logger.info(f"Creating new case for patient {case_request.patient_id}")
        
        with SqlAlchemyUnitOfWork() as uow:
            # Use case service to create new case
            case_service = CaseService(uow.cases)
            case_id, created = case_service.create_case(
                patient_id=case_request.patient_id,
                case_date=case_request.case_date,
                case_class=case_request.case_class,
                case_status=case_request.case_status,
                pathogen=case_request.pathogen,
                canton=case_request.canton
            )
            
            if created:
                uow.commit()
                logger.info(f"Created new case with ID: {case_id}")
                
                return CreateCaseResponse(
                    case_id=case_id,
                    patient_id=case_request.patient_id,
                    case_date=case_request.case_date,
                    case_class=case_request.case_class,
                    case_status=case_request.case_status,
                    pathogen=case_request.pathogen,
                    canton=case_request.canton,
                    created=True
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to create case")
                
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except ValueError as e:
        logger.error(f"Validation error creating case: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


