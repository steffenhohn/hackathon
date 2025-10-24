# pylint: disable=broad-except
"""Message bus for case_mgmt service following Cosmic Python pattern."""

from __future__ import annotations
import logging
from typing import List, Dict, Callable, Type, Union, TYPE_CHECKING

from shared.domain.commands import Command, Event
from case.service_layer import handlers
from case.domain.events import CaseCreated
from case.domain.commands import CreateCaseFromDataProduct

if TYPE_CHECKING:
    from case.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

Message = Union[CreateCaseFromDataProduct]


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
    CaseCreated: [
        handlers.publish_case_created_event
    ],
}  # type: Dict[Type[Event], List[Callable]]

# Command handlers - single handler per command type
COMMAND_HANDLERS = {
    CreateCaseFromDataProduct: handlers.create_case_from_data_product,
}  # type: Dict[Type[Command], Callable]
