# pylint: disable=broad-except
"""Message bus for lab_dp service following Cosmic Python pattern."""

from __future__ import annotations
import logging
from typing import List, Dict, Callable, Type, Union, TYPE_CHECKING

from shared.domain.commands import Command, Event
from lab_dp.domain.commands import CreateDataProduct
from lab_dp.domain.events import DataProductCreated
from lab_dp.service_layer import handlers

if TYPE_CHECKING:
    from lab_dp.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

Message = Union[CreateDataProduct]


def handle(
    message: Message,
    uow: AbstractUnitOfWork,
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
    uow: AbstractUnitOfWork,
):
    """Handle event by calling all registered event handlers."""
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug(f"handling event {event} with handler {handler}")
            handler(event, uow=uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logger.exception("Exception handling event %s", event)
            continue


def handle_command(
    command: Command,
    queue: List[Message],
    uow: AbstractUnitOfWork,
):
    """Handle command by calling the registered command handler."""
    logger.debug(f"handling command {command}")
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow=uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception("Exception handling command %s", command)
        raise


# Event handlers - multiple handlers can respond to same event
EVENT_HANDLERS = {
    DataProductCreated: [
        handlers.update_metrics_read_model,
        handlers.publish_data_product_event,
    ],
}  # type: Dict[Type[Event], List[Callable]]

# Command handlers - single handler per command type
COMMAND_HANDLERS = {
    CreateDataProduct: handlers.create_data_product,
}  # type: Dict[Type[Command], Callable]
