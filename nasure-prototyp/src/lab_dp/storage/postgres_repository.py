"""
PostgreSQL Repository for Laboratory Data Product
Stores surveillance reports with optimized queries
"""
import json
import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg
import logging

from lab_dp.domain.minimal_model import LaboratoryReport, LaboratoryObservation, TestCode, TestResult, Specimen, ResultInterpretation

logger = logging.getLogger(__name__)


class PostgreSQLRepository:
    """PostgreSQL repository for surveillance reports"""

    def __init__(self):
        self.connection_pool = None

    async def get_connection_pool(self):
        """Get or create connection pool"""
        if not self.connection_pool:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://lab_dp_user:lab_dp_pass@localhost:5432/lab_dp_db"
            )
            self.connection_pool = await asyncpg.create_pool(database_url)
        return self.connection_pool

    async def save_report(self, report: LaboratoryReport) -> None:
        """Save surveillance report to PostgreSQL"""
        pool = await self.get_connection_pool()

        async with pool.acquire() as conn:
            # Serialize observations
            observations_json = [
                {
                    "observation_id": obs.observation_id,
                    "test_code": {
                        "loinc_code": obs.test_code.loinc_code,
                        "loinc_display": obs.test_code.loinc_display,
                        "pathogen": obs.test_code.pathogen
                    },
                    "result": {
                        "interpretation": obs.result.interpretation.value,
                        "snomed_code": obs.result.snomed_code,
                        "snomed_display": obs.result.snomed_display
                    },
                    "test_date": obs.test_date.isoformat() if obs.test_date else None,
                    "specimen": {
                        "collection_date": obs.specimen.collection_date.isoformat() if obs.specimen and obs.specimen.collection_date else None
                    } if obs.specimen else None
                }
                for obs in report.observations
            ]

            # Insert surveillance report
            await conn.execute("""
                INSERT INTO surveillance_reports (
                    report_id, bundle_id, fhir_identifier,
                    patient_id, pathogen, performing_lab_id, ordering_facility_id,
                    report_timestamp, composition_date, ingestion_timestamp,
                    report_status, source_system, observations_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (bundle_id) DO UPDATE SET
                    patient_id = EXCLUDED.patient_id,
                    pathogen = EXCLUDED.pathogen,
                    performing_lab_id = EXCLUDED.performing_lab_id,
                    ordering_facility_id = EXCLUDED.ordering_facility_id,
                    report_timestamp = EXCLUDED.report_timestamp,
                    composition_date = EXCLUDED.composition_date,
                    report_status = EXCLUDED.report_status,
                    observations_data = EXCLUDED.observations_data,
                    updated_at = NOW()
            """,
                str(report.report_id),
                report.bundle_id,
                report.fhir_identifier,
                report.patient_id,
                report.pathogen,
                report.performing_lab_id,
                report.ordering_facility_id,
                report.report_timestamp,
                report.composition_date,
                report.ingestion_timestamp,
                report.report_status,
                report.source_system,
                json.dumps(observations_json)
            )

            logger.info(f"Saved report to PostgreSQL: {report.report_id}")

    async def get_report(self, report_id: str) -> Optional[LaboratoryReport]:
        """Get surveillance report by ID"""
        pool = await self.get_connection_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM surveillance_reports WHERE report_id = $1
            """, report_id)

            if not row:
                return None

            return self._row_to_report(row)

    async def list_reports(self, pathogen: str = None, limit: int = 100) -> List[LaboratoryReport]:
        """List surveillance reports with optional filtering"""
        pool = await self.get_connection_pool()

        async with pool.acquire() as conn:
            if pathogen:
                rows = await conn.fetch("""
                    SELECT * FROM surveillance_reports
                    WHERE pathogen = $1
                    ORDER BY report_timestamp DESC
                    LIMIT $2
                """, pathogen, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM surveillance_reports
                    ORDER BY report_timestamp DESC
                    LIMIT $1
                """, limit)

            return [self._row_to_report(row) for row in rows]

    def _row_to_report(self, row) -> LaboratoryReport:
        """Convert database row to LaboratoryReport"""
        # Deserialize observations
        observations_data = json.loads(row['observations_data'])
        observations = []

        for obs_data in observations_data:
            test_code = TestCode(
                loinc_code=obs_data['test_code']['loinc_code'],
                loinc_display=obs_data['test_code']['loinc_display'],
                pathogen=obs_data['test_code']['pathogen']
            )

            result = TestResult(
                interpretation=ResultInterpretation(obs_data['result']['interpretation']),
                snomed_code=obs_data['result'].get('snomed_code'),
                snomed_display=obs_data['result'].get('snomed_display')
            )

            specimen = None
            if obs_data.get('specimen') and obs_data['specimen'].get('collection_date'):
                specimen = Specimen(
                    collection_date=datetime.fromisoformat(obs_data['specimen']['collection_date'])
                )

            test_date = None
            if obs_data.get('test_date'):
                test_date = datetime.fromisoformat(obs_data['test_date'])

            observation = LaboratoryObservation(
                observation_id=obs_data['observation_id'],
                test_code=test_code,
                result=result,
                test_date=test_date,
                specimen=specimen
            )
            observations.append(observation)

        # Create report
        report = LaboratoryReport(
            report_id=UUID(row['report_id']),
            bundle_id=row['bundle_id'],
            fhir_identifier=row['fhir_identifier'],
            patient_id=row['patient_id'],
            pathogen=row['pathogen'],
            performing_lab_id=row['performing_lab_id'],
            ordering_facility_id=row['ordering_facility_id'],
            report_timestamp=row['report_timestamp'],
            composition_date=row['composition_date'],
            ingestion_timestamp=row['ingestion_timestamp'],
            report_status=row['report_status'],
            source_system=row['source_system']
        )

        # Add observations
        report.observations = observations

        return report


# Dependency injection
async def get_postgres_repository() -> PostgreSQLRepository:
    """FastAPI dependency to get PostgreSQL repository"""
    return PostgreSQLRepository()