"""Event processor for handling bundle stored events."""

import asyncio
import json
import logging
import redis
from typing import Dict, Any

from lab_dp.domain.commands import GenerateDataProduct
from shared.service_layer.messagebus import bus
from lab_dp.service_layer import data_product_handlers  # Import to register handlers
from config import get_redis_url

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes events from Redis pub/sub for data product generation."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or get_redis_url()
        self.redis_client = redis.from_url(self.redis_url)
        self.pubsub = self.redis_client.pubsub()

    async def start_processing(self):
        """Start processing events from Redis pub/sub."""
        logger.info("Starting event processor for data product generation")

        # Subscribe to bundle stored events
        self.pubsub.subscribe('bundle_stored')

        try:
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    await self._process_message(message)
        except KeyboardInterrupt:
            logger.info("Event processor stopped by user")
        except Exception as e:
            logger.error(f"Event processor error: {e}")
            raise
        finally:
            self.pubsub.close()

    async def _process_message(self, message: Dict[str, Any]):
        """Process a single event message."""
        try:
            data = json.loads(message['data'].decode('utf-8'))
            event_type = data.get('event_type')

            if event_type == 'bundle_stored':
                await self._handle_bundle_stored(data)
            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_bundle_stored(self, data: Dict[str, Any]):
        """Handle bundle stored event by generating data product."""
        logger.info(f"Processing bundle stored event: {data['bundle_id']}")

        # Create GenerateDataProduct command
        command = GenerateDataProduct(
            bundle_id=data['bundle_id'],
            object_key=data['object_key']
        )

        # Handle command through message bus
        try:
            await bus.handle(command)
            logger.info(f"Successfully processed bundle {data['bundle_id']}")
        except Exception as e:
            logger.error(f"Failed to generate data product for bundle {data['bundle_id']}: {e}")
            # In production, you might want to implement retry logic or dead letter queues


def main():
    """Main entry point for the Lab Data Product event processor."""
    import logging
    logging.basicConfig(level=logging.INFO)

    processor = EventProcessor()
    asyncio.run(processor.start_processing())


if __name__ == "__main__":
    main()