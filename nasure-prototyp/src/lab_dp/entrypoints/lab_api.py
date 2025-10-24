"""
Lab Data Product API - Read endpoints for data products and metrics.
Following Cosmic Python pattern: thin API layer delegates to views.
"""

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
import logging

from lab_dp import views
from lab_dp.service_layer.unit_of_work import SqlAlchemyUnitOfWork

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Laboratory Data Product API",
    description="Read API for laboratory surveillance data products and metrics",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lab-data-product-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/data-product/{product_id}")
def get_data_product(product_id: str):
    """
    Retrieve lab data product by product_id.

    Following Cosmic Python pattern: API layer is thin, delegates to repository.
    """
    uow = SqlAlchemyUnitOfWork()

    with uow:
        product = uow.products.get(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data product {product_id} not found"
        )

    return {
        "product_id": product.product_id,
        "patient_id": product.patient_id,
        "bundle_id": product.bundle_id,
        "timestamp": product.timestamp,
        "pathogen_code": product.pathogen_code,
        "pathogen_description": product.pathogen_description,
        "interpretation": product.interpretation,
        "version_number": product.version_number,
    }


@app.get("/api/v1/metrics/quality")
def get_quality_metrics():
    """
    Get overall quality metrics.

    Following Cosmic Python pattern: API delegates to views for read model queries.

    Returns:
        - last_updated: When the most recent report was created
        - average_delay_hours: Average processing delay
    """
    uow = SqlAlchemyUnitOfWork()
    metrics = views.get_quality_metrics(uow)

    return metrics


@app.get("/api/v1/metrics/pathogen/{pathogen_code}")
def get_pathogen_count(pathogen_code: str):
    """
    Get count of reports for a pathogen in last 24 hours.

    Following Cosmic Python pattern: API delegates to views for read model queries.

    Args:
        pathogen_code: Pathogen code (e.g., LOINC code)

    Returns:
        Count of reports in last 24 hours for the specified pathogen
    """
    uow = SqlAlchemyUnitOfWork()
    metrics = views.get_pathogen_count_last_24h(pathogen_code, uow)

    return metrics
