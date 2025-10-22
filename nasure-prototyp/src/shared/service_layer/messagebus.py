"""Simple message bus for command and event handling."""

import logging
from typing import Dict, Type, Callable, Union, List

from shared.domain.commands import Command

logger = logging.getLogger(__name__)


class MessageBus:
    """Simple message bus for routing commands and events to handlers."""

    def __init__(self):
        self.command_handlers: Dict[Type[Command], Callable] = {}
        self.event_handlers: Dict[Type, List[Callable]] = {}

    def register_handler(self, message_type: Type, handler: Callable):
        """Register a command handler."""
        self.command_handlers[message_type] = handler

    def register_event_handler(self, event_type: Type, handler: Callable):
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def handle(self, message: Union[Command, object]):
        """Handle a command by calling the registered handler."""
        message_type = type(message)

        # Handle commands
        if isinstance(message, Command):
            if message_type not in self.command_handlers:
                raise ValueError(f"No handler registered for command {message_type.__name__}")

            handler = self.command_handlers[message_type]

            try:
                logger.info(f"Handling command {message_type.__name__}")
                return handler(message)
            except Exception as e:
                logger.error(f"Error handling command {message_type.__name__}: {e}")
                raise

        # Handle events
        else:
            if message_type not in self.event_handlers:
                logger.warning(f"No handlers registered for event {message_type.__name__}")
                return

            results = []
            for handler in self.event_handlers[message_type]:
                try:
                    logger.info(f"Handling event {message_type.__name__} with {handler.__name__}")
                    result = handler(message)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error handling event {message_type.__name__} with {handler.__name__}: {e}")
                    # Continue with other handlers even if one fails
                    continue

            return results


# Global message bus instance
bus = MessageBus()