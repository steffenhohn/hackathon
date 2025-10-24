"""
Views for read operations - separate from command/write path.
Following Cosmic Python CQRS pattern: views query simple read model tables.

All aggregations are done here on the metrics table, which is kept up-to-date
by event handlers responding to DataProductCreated events.
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text

from lab_dp.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


def get_quality_metrics(uow: AbstractUnitOfWork) -> Dict[str, Any]:
    """
    Get overall quality metrics.

    Returns:
        - last_updated: When the most recent report was created
        - average_delay_hours: Average time between report timestamp and creation in system
    """
    with uow:
        session = uow.session

        # Get last updated timestamp
        last_updated = session.execute(
            text("SELECT MAX(created_at) FROM metrics")
        ).scalar()

        # Calculate average delay between report_timestamp and created_at
        # This shows how long it takes for reports to be processed
        avg_delay = session.execute(
            text("""
                SELECT AVG(
                    EXTRACT(EPOCH FROM (created_at - report_timestamp::timestamp)) / 3600
                )
                FROM metrics
                WHERE report_timestamp IS NOT NULL
            """)
        ).scalar()

        return {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "average_delay_hours": float(avg_delay) if avg_delay else None,
            "queried_at": datetime.utcnow().isoformat(),
        }


def get_pathogen_count_last_24h(
    pathogen_code: str,
    uow: AbstractUnitOfWork
) -> Dict[str, Any]:
    """
    Get count of reports for a pathogen in last 24 hours.

    Args:
        pathogen_code: Pathogen code to filter by
        uow: Unit of work

    Returns:
        Count of reports
    """
    with uow:
        session = uow.session
        since = datetime.utcnow() - timedelta(hours=24)

        count = session.execute(
            text("""
                SELECT COUNT(*)
                FROM metrics
                WHERE pathogen_code = :pathogen_code
                  AND created_at >= :since
            """),
            dict(pathogen_code=pathogen_code, since=since)
        ).scalar()

        return {
            "pathogen_code": pathogen_code,
            "count": count or 0,
            "time_window_hours": 24,
            "queried_at": datetime.utcnow().isoformat(),
        }
