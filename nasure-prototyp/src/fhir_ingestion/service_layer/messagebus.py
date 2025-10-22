# pylint: disable=broad-except
"""Message bus for FHIR ingestion service following Cosmic Python pattern."""

from __future__ import annotations
import logging
from typing import List, Dict, Callable, Type, Union, TYPE_CHECKING

from shared.domain.commands import Command, Event
from fhir_ingestion.domain.commands import StoreFHIRBundle
from fhir_ingestion.domain.events import BundleStored
from fhir_ingestion.service_layer import handlers

if TYPE_CHECKING:
    from fhir_ingestion.service_layer.unit_of_work import FHIRIngestionUnitOfWork

logger = logging.getLogger(__name__)

Message = Union[StoreFHIRBundle, BundleStored]


def handle(
    message: Message,
    uow: FHIRIngestionUnitOfWork,
):
    """Handle message (command or event) with the appropriate handler."""
    results = []
    queue = [message]

    while queue:
        message = queue.pop(0)

        if isinstance(message, Event):
            handle_event(message, queue, uow)
        elif isinstance(message, Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")

    return results


def handle_event(
    event: Event,
    queue: List[Message],
    uow: FHIRIngestionUnitOfWork,
):
    """Handle event by calling all registered event handlers."""
    logger.info(f"handling event {type(event).__name__} with {len(EVENT_HANDLERS.get(type(event), []))} handlers")
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.info(f"calling handler {handler.__name__} for event {type(event).__name__}")
            handler(event, uow=uow)
            new_events = uow.collect_new_events()
            logger.info(f"Handler {handler.__name__} generated {len(new_events)} new events")
            queue.extend(new_events)
        except Exception:
            logger.exception("Exception handling event %s", event)
            continue


def handle_command(
    command: Command,
    queue: List[Message],
    uow: FHIRIngestionUnitOfWork,
):
    """Handle command by calling the registered command handler."""
    logger.info(f"handling command {command}")
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow=uow)
        new_events = uow.collect_new_events()
        logger.info(f"Collected {len(new_events)} events after command: {[type(e).__name__ for e in new_events]}")
        queue.extend(new_events)
        return result
    except Exception:
        logger.exception("Exception handling command %s", command)
        raise


# Event handlers - individual event handlers
EVENT_HANDLERS = {
    BundleStored: [
        handlers.bundle_stored,
        handlers.publish_stored_event,
    ],
}  # type: Dict[Type[Event], List[Callable]]

# Command handlers - single handler per command type
COMMAND_HANDLERS = {
    StoreFHIRBundle: handlers.store_fhir_bundle,
}  # type: Dict[Type[Command], Callable]