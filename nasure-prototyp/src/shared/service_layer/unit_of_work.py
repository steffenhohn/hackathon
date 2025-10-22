from __future__ import annotations

"""Abstract Unit of Work pattern for coordinating operations across repositories."""

import abc


class AbstractUnitOfWork(abc.ABC):
    """Abstract Unit of Work for coordinating operations across repositories."""

    def __enter__(self) -> AbstractUnitOfWork:
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        self._commit()

    def collect_new_events(self):
        """Collect domain events from aggregates."""
        # Future: collect events from domain entities
        return []

    @abc.abstractmethod
    def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError