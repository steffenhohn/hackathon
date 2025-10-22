"""Command handlers for lab data product generation."""

import logging
from lab_dp.domain.commands import GenerateDataProduct
from lab_dp.service_layer.unit_of_work import LabDataProductUnitOfWork
from lab_dp.service_layer.data_product_service import DataProductService
from shared.service_layer.messagebus import bus

logger = logging.getLogger(__name__)


async def handle_generate_data_product(command: GenerateDataProduct):
    """
    Handle GenerateDataProduct command.

    Generates surveillance data product from stored FHIR bundle.
    """
    logger.info(f"Generating data product for bundle {command.bundle_id}")

    with LabDataProductUnitOfWork() as uow:
        data_product_service = DataProductService(
            bundles_repo=uow.bundles,
            postgres_repo=uow.postgres_repo
        )

        # Generate data product from stored FHIR bundle
        report_id = await data_product_service.generate_data_product(
            bundle_id=command.bundle_id,
            object_key=command.object_key
        )

        uow.commit()

    logger.info(f"Generated data product {report_id} for bundle {command.bundle_id}")
    return report_id


# Register command handlers
bus.register_handler(GenerateDataProduct, handle_generate_data_product)