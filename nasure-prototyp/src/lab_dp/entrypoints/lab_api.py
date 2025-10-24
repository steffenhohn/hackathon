"""
Lab Data Product API - Read endpoints for data products and metrics.
Following Cosmic Python pattern: thin API layer delegates to views.
"""

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
import logging

from lab_dp import views
from lab_dp.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from lab_dp.adapters import orm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize ORM mappers (Cosmic Python pattern)
orm.start_mappers()
logger.info("ORM mappers initialized")

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


@app.get("/api/v1/data-products")
def get_data_products(limit: int = 100, offset: int = 0):
    """
    Retrieve all lab data products with pagination.

    Following Cosmic Python CQRS pattern: API delegates to views for read queries.

    Args:
        limit: Maximum number of products to return (default: 100)
        offset: Number of products to skip (default: 0)

    Returns:
        List of data products with pagination info
    """
    uow = SqlAlchemyUnitOfWork()
    result = views.get_all_data_products(uow, limit, offset)

    return result


@app.get("/api/v1/data-product/{product_id}")
def get_data_product(product_id: str):
    """
    Retrieve lab data product by product_id.

    Following Cosmic Python pattern: API layer is thin, delegates to repository.
    Serializes object to dict inside session context to avoid DetachedInstanceError.
    """
    uow = SqlAlchemyUnitOfWork()

    with uow:
        product = uow.products.get(product_id)

        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Data product {product_id} not found"
            )

        # Serialize to dict INSIDE session context (Cosmic Python pattern)
        serialized_product = {
            "product_id": product.product_id,
            "patient_id": product.patient_id,
            "bundle_id": product.bundle_id,
            "timestamp": product.timestamp,
            "pathogen_code": product.pathogen_code,
            "pathogen_description": product.pathogen_description,
            "interpretation": product.interpretation,
            "version_number": product.version_number,
        }

    return serialized_product


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


@app.get("/api/v1/data-products/pathogen/{pathogen_code}")
def get_data_products_by_pathogen(pathogen_code: str, limit: int = 100, offset: int = 0):
    """
    Get all data products for a specific pathogen.

    Following Cosmic Python CQRS pattern: API delegates to views for read queries.

    Args:
        pathogen_code: Pathogen code to filter by
        limit: Maximum number of products to return (default: 100)
        offset: Number of products to skip (default: 0)

    Returns:
        List of data products filtered by pathogen code
    """
    uow = SqlAlchemyUnitOfWork()
    result = views.get_data_products_by_pathogen(pathogen_code, uow, limit, offset)

    return result


@app.get("/api/v1/data-products/patient/{patient_id}/pathogen/{pathogen_code}")
def get_data_products_by_patient_and_pathogen(
    patient_id: str,
    pathogen_code: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get all data products for a specific patient and pathogen.

    Following Cosmic Python CQRS pattern: API delegates to views for read queries.

    Args:
        patient_id: Patient ID to filter by
        pathogen_code: Pathogen code to filter by
        limit: Maximum number of products to return (default: 100)
        offset: Number of products to skip (default: 0)

    Returns:
        List of data products filtered by patient and pathogen
    """
    uow = SqlAlchemyUnitOfWork()
    result = views.get_data_products_by_patient_and_pathogen(
        patient_id, pathogen_code, uow, limit, offset
    )

    return result
