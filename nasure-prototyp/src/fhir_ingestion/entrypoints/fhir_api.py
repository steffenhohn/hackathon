"""
FHIR API Entrypoint - Thin API with Command Dispatch
API receives payloads and dispatches commands through message bus
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import logging

from fhir_ingestion.domain.commands import StoreFHIRBundle
from fhir_ingestion.service_layer import messagebus, views
from fhir_ingestion.service_layer.unit_of_work import FHIRIngestionUnitOfWork

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Laboratory FHIR API",
    description="Command-based CH-eLM FHIR bundle processing",
    version="2.3.0"
)


class IngestionResponse(BaseModel):
    """Response model for successful ingestion"""
    status: str
    bundle_id: str
    message: str
    received_at: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lab-dp-fhir-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/v1/fhir/ingest", response_model=IngestionResponse)
def ingest_fhir_bundle(bundle: Dict[str, Any], source_system: str = "ch-elm"):
    """
    Ingest CH-eLM FHIR Bundle - Thin API with command dispatch.

    Accepts FHIR Bundle directly as per FHIR REST API standard.
    The bundle is sent as the root JSON object in the request body.

    Following Cosmic Python pattern: API receives payload and dispatches command.
    """
    try:
        # Generate unique bundle ID
        bundle_id = str(uuid.uuid4())
        received_at = datetime.now(timezone.utc)

        logger.info(f"Received FHIR bundle: {bundle_id}")

        # Create and dispatch command - all business logic handled by command handler
        cmd = StoreFHIRBundle(
            bundle_id=bundle_id,
            bundle_data=bundle,
            source_system=source_system,
            received_at=received_at,
            source_ip="laboratoryReport"
        )

        # Handle command through dedicated FHIR ingestion message bus
        uow = FHIRIngestionUnitOfWork()
        results = messagebus.handle(cmd, uow)

        logger.info(f"Command processed for bundle {bundle_id}, results: {results}")

        return IngestionResponse(
            status="accepted",
            bundle_id=bundle_id,
            message="FHIR bundle processing started",
            received_at=received_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to process FHIR bundle: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )


@app.get("/api/v1/fhir/bundle/{bundle_id}")
def get_bundle_endpoint(bundle_id: str):
    """
    Retrieve FHIR bundle by bundle_id.

    Following Cosmic Python pattern: API layer is thin, delegates to views.
    """
    uow = FHIRIngestionUnitOfWork()
    bundle_data = views.get_bundle(bundle_id, uow)

    if bundle_data is None:
        raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} not found")

    return bundle_data
