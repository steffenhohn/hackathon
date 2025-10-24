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
    Get overall quality metrics with two types of latency:

    1. Reporting Latency: Time from lab report creation to storage in our system
       (stored_at - report_timestamp)

    2. Processing Latency: Time from storage to data product creation
       (created_at - stored_at)

    Returns:
        - last_updated: When the most recent report was created
        - avg_reporting_latency_hours: Average time from lab report to storage
        - avg_processing_latency_seconds: Average time from storage to data product
    """
    with uow:
        session = uow.session

        # Get last updated timestamp
        last_updated = session.execute(
            text("SELECT MAX(created_at) FROM metrics")
        ).scalar()

        # Calculate average reporting latency (lab report to storage)
        # This shows how long it takes for lab reports to reach our system
        avg_reporting_latency = session.execute(
            text("""
                SELECT AVG(
                    EXTRACT(EPOCH FROM (stored_at - report_timestamp::timestamp)) / 3600
                )
                FROM metrics
                WHERE report_timestamp IS NOT NULL AND stored_at IS NOT NULL
            """)
        ).scalar()

        # Calculate average processing latency (storage to data product)
        # This shows how long our lab_dp service takes to process bundles
        avg_processing_latency = session.execute(
            text("""
                SELECT AVG(
                    EXTRACT(EPOCH FROM (created_at - stored_at))
                )
                FROM metrics
                WHERE stored_at IS NOT NULL AND created_at IS NOT NULL
            """)
        ).scalar()

        return {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "avg_reporting_latency_hours": float(avg_reporting_latency) if avg_reporting_latency else None,
            "avg_processing_latency_seconds": float(avg_processing_latency) if avg_processing_latency else None,
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
