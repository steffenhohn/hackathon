"""Redis adapter for publishing events following Cosmic Python pattern."""

import json
import logging
from dataclasses import asdict
from datetime import datetime
import redis

from config import get_redis_host_and_port
from shared.domain.commands import Event

logger = logging.getLogger(__name__)

r = redis.Redis(**get_redis_host_and_port())


def _serialize_event(event: Event) -> str:
    """Serialize event to JSON, handling datetime objects."""
    event_dict = asdict(event)

    # Convert datetime objects to ISO strings
    for key, value in event_dict.items():
        if isinstance(value, datetime):
            event_dict[key] = value.isoformat()

    return json.dumps(event_dict)


def publish(channel: str, event: Event):
    """Publish event to Redis channel."""
    logger.info("publishing: channel=%s, event=%s", channel, event)
    message = _serialize_event(event)
    r.publish(channel, message)