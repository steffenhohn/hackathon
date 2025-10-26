"""Redis event consumer for case mgmt service - listens to DataProductCreated events."""

import json
import logging
import redis
from sqlalchemy import create_engine
from datetime import datetime, timezone
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

    # Initialize database and ORM mappers (Cosmic Python pattern)
    logger.info("Initializing database schema and ORM mappers...")
    engine = create_engine(config.get_postgres_uri())
    orm.metadata.create_all(engine)
    orm.start_mappers()
    logger.info("✓ Database tables created and ORM mappers initialized")

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("surveillance:data-products")

    logger.info("Subscribed to 'surveillance:data-products' channel, waiting for messages...")

    for m in pubsub.listen():
        handle_data_product_created(m)

def parse_timestamp(timestamp_str, field_name="timestamp"):
    """Parse timestamp string to datetime object with error handling."""
    if not timestamp_str:
        logger.warning(f"No {field_name} provided, using current time")
        return datetime.now(timezone.utc)
    
    try:
        # Handle different timestamp formats
        if timestamp_str.endswith('Z'):
            # ISO format with Z suffix
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        elif '+' in timestamp_str or timestamp_str.endswith('00:00'):
            # ISO format with timezone
            return datetime.fromisoformat(timestamp_str)
        else:
            # Assume naive datetime, make it UTC
            dt = datetime.fromisoformat(timestamp_str)
            return dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error(f"Failed to parse {field_name} '{timestamp_str}': {e}")
        return datetime.now(timezone.utc)

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
        lab_timestamp = parse_timestamp(timestamp, "lab_timestamp")
        stored_at = parse_timestamp(stored_at_str, "stored_at")
        created_at = parse_timestamp(created_at_str, "created_at")

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
        logger.info(f"  - timestamp: {lab_timestamp}")
        logger.info(f"  - stored_at: {stored_at}")
        logger.info(f"  - created_at: {created_at}")

        # Create command to process the case
        cmd = commands.CreateCaseFromDataProduct(
            product_id=product_id,
            patient_id=patient_id,
            pathogen_code=pathogen_code,
            pathogen_description=pathogen_description,
            lab_timestamp=lab_timestamp,
            stored_at=stored_at,
            created_at=created_at
        )

        # Create unit of work and handle command
        uow = SqlAlchemyUnitOfWork()
        results = messagebus.handle(cmd, uow)

        logger.info(f"Successfully processed product {product_id}, results: {results}")

    except Exception as e:
        logger.error(f"Error handling created data product event: {e}", exc_info=True)

if __name__ == "__main__":
    main()