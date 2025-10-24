import logging
from sqlalchemy import text

from lab_dp.domain.commands import CreateDataProduct
from lab_dp.service_layer.unit_of_work import AbstractUnitOfWork
from lab_dp.adapters.fhir_client import FHIRClientError
from lab_dp.adapters.fhir_transformer import FHIRTransformer, FHIRTransformationError

logger = logging.getLogger(__name__)


def create_data_product(
    command: CreateDataProduct,
    uow: AbstractUnitOfWork
) -> str:
    """
    Create lab data product from stored FHIR bundle.

    Flow:
    1. Fetch FHIR bundle from fhir_ingestion service via API
    2. Transform bundle to LabDataProduct domain entity
    3. Store product in database via repository
    4. Commit transaction

    Args:
        command: CreateDataProduct command with bundle_id
        uow: Unit of work for transaction management (includes fhir_client)

    Returns:
        product_id: The ID of the created data product

    Raises:
        FHIRClientError: If bundle cannot be fetched
        FHIRTransformationError: If bundle cannot be transformed
    """
    logger.info(f"Processing CreateDataProduct command for bundle {command.bundle_id}")

    try:
        # Initialize UoW to get access to fhir_client (but outside transaction)
        with uow:
            # Step 1: Fetch FHIR bundle from ingestion service
            bundle_data = uow.fhir_client.get_bundle(command.bundle_id)
            logger.info(f"Fetched bundle {command.bundle_id} from FHIR ingestion service")

            # Step 2: Transform FHIR bundle to domain entity
            transformer = FHIRTransformer()
            lab_product = transformer.extract_lab_data_product(bundle_data, command.bundle_id)
            logger.info(f"Transformed bundle {command.bundle_id} to product {lab_product.product_id}")

            # Step 3: Call domain method to mark product as created (generates events)
            lab_product.create()

            # Step 4: Store product via repository - returns product_id (Cosmic Python pattern)
            product_id = uow.products.add(lab_product)
            logger.info(f"Added product {product_id} to repository")

            # Commit transaction
            uow.commit()
            logger.info(f"Committed product {product_id} to database")

        logger.info(f"Successfully created data product {product_id} from bundle {command.bundle_id}")
        return product_id

    except FHIRClientError as e:
        logger.error(f"Failed to fetch bundle {command.bundle_id}: {e}")
        raise

    except FHIRTransformationError as e:
        logger.error(f"Failed to transform bundle {command.bundle_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error processing bundle {command.bundle_id}: {e}")
        raise


def update_metrics_read_model(event, uow: AbstractUnitOfWork):
    """
    Update metrics read model when a data product is created.

    Following Cosmic Python pattern: event handler inserts into denormalized
    read model table. Aggregations are done in views.py.

    Args:
        event: DataProductCreated event
        uow: Unit of work
    """
    logger.info(f"Updating metrics read model for product {event.product_id}")

    with uow:
        uow.session.execute(
            text("""
                INSERT INTO metrics
                    (product_id, pathogen_code, pathogen_description, report_timestamp, created_at)
                VALUES
                    (:product_id, :pathogen_code, :pathogen_description, :report_timestamp, :created_at)
            """),
            dict(
                product_id=event.product_id,
                pathogen_code=event.pathogen_code,
                pathogen_description=event.pathogen_description,
                report_timestamp=event.timestamp,
                created_at=event.created_at,
            ),
        )
        uow.commit()

    logger.info(f"Metrics read model updated for product {event.product_id}")


def publish_data_product_event(event, uow: AbstractUnitOfWork):
    """
    Publish DataProductCreated event to external systems.

    Following Cosmic Python pattern: publish domain events to Redis
    for consumption by external services (e.g., alerting, dashboards).

    Args:
        event: DataProductCreated event
        uow: Unit of work
    """
    logger.info(f"Publishing DataProductCreated event for product {event.product_id}")
    try:
        # Import here to avoid circular dependency
        from lab_dp.adapters import redis_adapter

        redis_adapter.publish("surveillance:data-products", event)
        logger.info(f"Published DataProductCreated event for {event.product_id}")

    except Exception as e:
        logger.error(f"Failed to publish event for {event.product_id}: {e}")
        # Don't re-raise - external failures shouldn't break the flow