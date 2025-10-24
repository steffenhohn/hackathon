"""Redis event consumer for lab_dp service - listens to BundleStored events."""

import json
import logging
import redis
from sqlalchemy import create_engine

import config
from lab_dp.service_layer import messagebus
from lab_dp.domain import commands
from lab_dp.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from lab_dp.adapters import orm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def main():
    """Main entry point for Redis event consumer."""
    logger.info("Lab DP Redis pubsub consumer starting")

    # Initialize database and ORM mappers (Cosmic Python pattern)
    logger.info("Initializing database schema and ORM mappers...")
    engine = create_engine(config.get_postgres_uri())
    orm.metadata.create_all(engine)
    orm.start_mappers()
    logger.info("✓ Database tables created and ORM mappers initialized")

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("surveillance:bundles")

    logger.info("Subscribed to 'surveillance:bundles' channel, waiting for messages...")

    for m in pubsub.listen():
        handle_bundle_stored(m)


def handle_bundle_stored(m):
    """
    Handle BundleStored event from Redis.

    When a bundle is stored in fhir_ingestion, it publishes a BundleStored event
    to Redis. This handler receives it and creates a data product.

    Only processes bundles with bundle_type '4241000179101' (Laborbericht).

    Args:
        m: Redis message dictionary
    """
    logger.info("Received message: %s", m)

    try:
        # Parse message data
        data = json.loads(m["data"])
        bundle_id = data.get("bundle_id")
        bundle_type = data.get("bundle_type")
        stored_at_str = data.get("stored_at")

        if not bundle_id:
            logger.error("No bundle_id in message: %s", data)
            return

        # Filter: Only process Laborbericht (4241000179101)
        logger.info(f"Checking if bundle {bundle_id} is a Laborbericht, bundle_type={bundle_type}")
        if not is_laborbericht(bundle_type):
            logger.info(f"Skipping bundle {bundle_id} - not a Laborbericht (bundle_type={bundle_type})")
            return

        logger.info(f"Processing BundleStored event for Laborbericht bundle {bundle_id}")

        # Parse stored_at timestamp from BundleStored event
        from datetime import datetime
        stored_at = datetime.fromisoformat(stored_at_str.replace('Z', '+00:00')) if stored_at_str else datetime.utcnow()

        # Create command to process the bundle
        cmd = commands.CreateDataProduct(bundle_id=bundle_id, stored_at=stored_at)

        # Create unit of work and handle command
        uow = SqlAlchemyUnitOfWork()
        results = messagebus.handle(cmd, uow)

        logger.info(f"Successfully processed bundle {bundle_id}, results: {results}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from message: {e}")
    except Exception as e:
        logger.error(f"Error handling bundle stored event: {e}", exc_info=True)


def is_laborbericht(bundle_type):
    """
    Check if bundle_type is a Laborbericht (Swiss laboratory report).

    Args:
        bundle_type: List or tuple (code, display), e.g., ['4241000179101', 'Laborbericht']
                     Note: JSON deserializes tuples as lists

    Returns:
        bool: True if bundle_type code is 4241000179101 (CH-eLM Laborbericht)
    """
    LABORBERICHT_CODE = "4241000179101"  # Swiss CH-eLM code for Laborbericht

    if not bundle_type:
        logger.debug("bundle_type is None or empty")
        return False

    # Handle both tuple (from Python) and list (from JSON deserialization)
    if isinstance(bundle_type, (tuple, list)) and len(bundle_type) >= 1:
        result = bundle_type[0] == LABORBERICHT_CODE
        logger.debug(f"bundle_type check: {bundle_type[0]} == {LABORBERICHT_CODE} -> {result}")
        return result

    logger.debug(f"bundle_type has unexpected format: {type(bundle_type)}, value: {bundle_type}")
    return False


if __name__ == "__main__":
    main()