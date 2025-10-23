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

    Args:
        m: Redis message dictionary
    """
    logger.info("Received message: %s", m)

    try:
        # Parse message data
        data = json.loads(m["data"])
        bundle_id = data.get("bundle_id")

        if not bundle_id:
            logger.error("No bundle_id in message: %s", data)
            return

        logger.info(f"Processing BundleStored event for bundle {bundle_id}")

        # Create command to process the bundle
        cmd = commands.CreateDataProduct(bundle_id=bundle_id)

        # Create unit of work and handle command
        uow = SqlAlchemyUnitOfWork()
        results = messagebus.handle(cmd, uow)

        logger.info(f"Successfully processed bundle {bundle_id}, results: {results}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from message: {e}")
    except Exception as e:
        logger.error(f"Error handling bundle stored event: {e}", exc_info=True)


if __name__ == "__main__":
    main()