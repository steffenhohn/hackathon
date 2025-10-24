"""Redis event consumer for case mgmt service - listens to DataProductCreated events."""

import json
import logging
import redis
from sqlalchemy import create_engine

import config
from case.service_layer import messagebus
from case.domain import commands
from case.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from case.adapters import orm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def main():
    """Main entry point for Redis event consumer."""
    logger.info("Case Mgmt Redis pubsub consumer starting")

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("surveillance:data-products")

    logger.info("Subscribed to 'surveillance:data-products' channel, waiting for messages...")

    for m in pubsub.listen():
        handle_data_product_created(m)


def handle_data_product_created(m):
    """
    Handle DataProductCreated event from Redis.

    When a data product is created in lab_dp, it publishes a DataProductCreated event
    to Redis. This handler receives it and processes the event.

    Args:
        m: Redis message dictionary
    """
    logger.info("Received message: %s", m)

    try:
        # Parse message data
        data = json.loads(m["data"])

        # Extract all available variables from the event
        product_id = data.get("product_id")
        patient_id = data.get("patient_id")
        pathogen_code = data.get("pathogen_code")
        pathogen_description = data.get("pathogen_description")
        timestamp = data.get("timestamp")  # Lab report timestamp (from FHIR bundle)
        stored_at_str = data.get("stored_at")  # When the bundle was stored by fhir_ingestion
        created_at_str = data.get("created_at")  # When the data product was created

        # Parse timestamps
        from datetime import datetime
        stored_at = datetime.fromisoformat(stored_at_str.replace('Z', '+00:00')) if stored_at_str else datetime.utcnow()
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) if created_at_str else datetime.utcnow()

        # Validate required fields
        if not product_id:
            logger.error("No product_id in message: %s", data)
            return
        if not patient_id:
            logger.error("No patient_id in message: %s", data)
            return 
        if not pathogen_code:
            logger.error("No pathogen_code in message: %s", data)
            return

        logger.info(f"Processing DataProductCreated event:")
        logger.info(f"  - product_id: {product_id}")
        logger.info(f"  - patient_id: {patient_id}")
        logger.info(f"  - pathogen_code: {pathogen_code}")
        logger.info(f"  - pathogen_description: {pathogen_description}")
        logger.info(f"  - timestamp: {timestamp}")
        logger.info(f"  - stored_at: {stored_at}")
        logger.info(f"  - created_at: {created_at}")

        # Create command to process the case
        cmd = commands.CreateCaseFromDataProduct(
            product_id=product_id,
            patient_id=patient_id,
            pathogen_code=pathogen_code,
            pathogen_description=pathogen_description,
            timestamp=timestamp,
            stored_at=stored_at,
            created_at=created_at
        )

        # Create unit of work and handle command
        uow = SqlAlchemyUnitOfWork()
        results = messagebus.handle(cmd, uow)

        logger.info(f"Successfully processed product {product_id}, results: {results}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from message: {e}")
    except Exception as e:
        logger.error(f"Error handling created data product event: {e}", exc_info=True)

if __name__ == "__main__":
    main()