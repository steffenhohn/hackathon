"""
Patient Service API Entrypoint - Thin API with Command Dispatch
"""
import config
from typing import Dict, Any
from sqlalchemy import create_engine
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, RootModel
import logging
import os
from shared.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from shared.adapters import orm
from shared.services.pseudonymization import PatientService

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Patient Service API",
    description="Patient resolution and pseudonymization service",
    version="1.0.0"
)

# Initialize database and ORM mappers (Cosmic Python pattern)
@app.on_event("startup")
async def startup_event():
    engine = create_engine(config.get_postgres_uri())
    orm.metadata.create_all(engine)
    orm.start_mappers()
    logger.info("✓ Patient Service Database initialized")

# ---------- Request/Response models ----------

class ResolveRequest(BaseModel):
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str   # YYYY-MM-DD
    canton: str

class ResolveResponse(BaseModel):
    patient_id: str

class PatientDetailsResponse(BaseModel):
    ahv_number: str
    family_name: str
    given_name: str
    gender: str
    birthdate: str
    canton: str

class FHIRPatient(RootModel[Dict[str, Any]]):
    """
    Accept arbitrary Patient payload; validated/parsed by extractor.
    Using RootModel keeps this decoupled from a full FHIR model for now.
    You can tighten this later with pydantic-fhir if desired.
    """
    pass


# ---------- Endpoints ----------

@app.get("/api/v1/patient/ahv/{ahv_number}", response_model=ResolveResponse, summary="Lookup patient_id by AHV number")
def get_patient_id_by_ahv(ahv_number: str):
    """
    Lookup if patient exists with given AHV number and return patient_id.

    """
    try:
        
        with SqlAlchemyUnitOfWork() as uow:
            # Lookup patient by AHV number
            patient_id = uow.patients.get_patient_id_by_ahv(ahv_number)
            
            if not patient_id:
                raise HTTPException(status_code=404, detail="No patient found for given AHV")
                
            return ResolveResponse(patient_id=patient_id)
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error looking up patient with AHV {ahv_number}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")  
    
@app.post("/api/v1/patient/pseudonymize", response_model=ResolveResponse, summary="Pseudonymize patient from FHIR resource")
def pseudonymize_patient(fhir_patient: FHIRPatient):
    """
    Pseudonymize patient from FHIR Patient resource.
    
    If patient exists (mapping by AHV number), return existing patient_id.
    If not, create new patient and return new patient_id.
    """
    try:
        
        logger.info("Received pseudonymization request for FHIR patient resource."f"{fhir_patient.root}") 

        with SqlAlchemyUnitOfWork() as uow:
            # Use the pseudonymization service to resolve/create patient
            patient_service = PatientService(uow.patients)  
            patient_id, created = patient_service.pseudonymize_patient(fhir_patient.root)            
            
            # Commit the transaction if a new patient was created
            if created:
                uow.commit()
                logger.info(f"Created new patient with ID: {patient_id}")
            else:
                logger.info(f"Found existing patient with ID: {patient_id}")
            
            return ResolveResponse(patient_id=patient_id)
            
    except ValueError as e:
        # Handle validation errors from patient service
        logger.error(f"Validation error resolving patient: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error resolving patient: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@app.get("/api/v1/patient/{patient_id}", response_model=PatientDetailsResponse, summary="Get patient details by patient_id")
def get_patient_by_id(patient_id: str):
    """
    Get patient details by patient_id.
    Returns all patient attributes or 404 if patient not found.
    """
    try:
        
        with SqlAlchemyUnitOfWork() as uow:
            # Create patient repository
            patient_record = uow.patients.get_patient_details_by_patient_id(patient_id)
                      
            if not patient_record:
                raise HTTPException(status_code=404, detail=f"Patient with ID {patient_id} not found")
            
            # Return patient data in PatientDetailsResponse format (which has all 6 attributes)
            return PatientDetailsResponse(
                ahv_number=patient_record.ahv_number,
                family_name=patient_record.family_name,
                given_name=patient_record.given_name,
                gender=patient_record.gender,
                birthdate=patient_record.birthdate,
                canton=patient_record.canton
            )
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")