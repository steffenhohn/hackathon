"""Data product service for generating surveillance data from stored FHIR bundles."""

import logging
from typing import Dict, Any, Optional

from fhir_ingestion.adapters.repository import AbstractRepository
from lab_dp.storage.postgres_repository import PostgreSQLRepository
from lab_dp.fhir.minimal_transformer import MinimalTransformer
from lab_dp.domain.minimal_model import LaboratoryReport
from fhir_ingestion.adapters.redis_publisher import RedisPublisher
from shared.services.pseudonymization import pseudonymize_patient, pseudonymize_organization
from config import get_redis_url

logger = logging.getLogger(__name__)


class DataProductService:
    """
    Service for generating surveillance data products from stored FHIR bundles.
    Calls pseudonymization functions directly.
    """

    def __init__(
        self,
        bundles_repo: AbstractRepository,
        postgres_repo: PostgreSQLRepository,
        redis_url: str = None
    ):
        self.bundles_repo = bundles_repo
        self.postgres_repo = postgres_repo
        self.transformer = MinimalTransformer()
        redis_url = redis_url or get_redis_url()
        self.redis_publisher = RedisPublisher(redis_url)

    async def generate_data_product(self, bundle_id: str, object_key: str) -> str:
        """
        Generate surveillance data product from stored FHIR bundle.

        Args:
            bundle_id: Unique bundle identifier
            object_key: MinIO object key for the stored FHIR bundle

        Returns:
            Generated report ID
        """
        logger.info(f"Generating data product for bundle {bundle_id}")

        try:
            # 1. Retrieve FHIR bundle from repository
            fhir_bundle = self.bundles_repo.get(object_key)
            logger.info(f"Retrieved FHIR bundle from repository: {object_key}")

            # 2. Transform FHIR to surveillance data product
            lab_report = self.transformer.transform_bundle(fhir_bundle)
            logger.info(f"Transformed FHIR bundle to laboratory report")

            # 3. Extract Patient resource and pseudonymize
            patient_resources = [resource for resource in fhir_bundle.get("entry", [])
                               if resource.get("resource", {}).get("resourceType") == "Patient"]

            if patient_resources:
                patient_resource = patient_resources[0]["resource"]
                pseudonym, method = pseudonymize_patient(patient_resource)
                lab_report.patient_id = pseudonym
                logger.info(f"Pseudonymized patient using {method}")
            else:
                logger.warning(f"No Patient resource found in bundle {bundle_id}")

            # 4. Extract Organization resources and pseudonymize
            organization_resources = [resource for resource in fhir_bundle.get("entry", [])
                                    if resource.get("resource", {}).get("resourceType") == "Organization"]

            if organization_resources:
                # Pseudonymize performing lab (first organization)
                performing_lab_org = organization_resources[0]["resource"]
                lab_pseudonym, lab_method = pseudonymize_organization(performing_lab_org)
                lab_report.performing_lab_id = lab_pseudonym
                logger.info(f"Pseudonymized performing lab using {lab_method}")

                # If multiple organizations, pseudonymize ordering facility
                if len(organization_resources) > 1:
                    ordering_facility_org = organization_resources[1]["resource"]
                    facility_pseudonym, facility_method = pseudonymize_organization(ordering_facility_org)
                    lab_report.ordering_facility_id = facility_pseudonym
                    logger.info(f"Pseudonymized ordering facility using {facility_method}")
            else:
                logger.warning(f"No Organization resources found in bundle {bundle_id}")

            # 5. Store surveillance data product in PostgreSQL
            report_id = self.postgres_repo.store_laboratory_report(lab_report)
            logger.info(f"Stored surveillance report with ID: {report_id}")

            # 6. Publish data product updated message to Redis for external consumers
            self.redis_publisher.publish_data_product_updated(
                report_id=report_id,
                bundle_id=bundle_id,
                pathogen=lab_report.pathogen or "unknown",
                patient_id=lab_report.patient_id or "unknown",
                metadata={
                    "performing_lab_id": lab_report.performing_lab_id,
                    "ordering_facility_id": lab_report.ordering_facility_id,
                    "observation_count": len(lab_report.observations),
                    "collection_date": lab_report.collection_date.isoformat() if lab_report.collection_date else None
                }
            )

            return report_id

        except Exception as e:
            logger.error(f"Failed to generate data product for bundle {bundle_id}: {e}")
            raise


    def get_surveillance_report(self, report_id: str) -> LaboratoryReport:
        """
        Retrieve surveillance report by ID.

        Args:
            report_id: The report identifier

        Returns:
            Laboratory report
        """
        return self.postgres_repo.get_laboratory_report(report_id)