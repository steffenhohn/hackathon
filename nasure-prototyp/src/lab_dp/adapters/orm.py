import logging
from sqlalchemy import (
    Table,
    MetaData,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    event,
)
from sqlalchemy.orm import registry
from lab_dp.domain import domain

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 pattern: use registry
mapper_registry = registry()
metadata = mapper_registry.metadata

products = Table(
    "products",
    metadata,
    Column("product_id", String(255), primary_key=True),
    Column("patient_id", String(255)),
    Column("bundle_id", String(255)),
    Column("pathogen_code", String(255)),
    Column("pathogen_description", String(255)),
    Column("interpretation", String(255)),
    Column("timestamp", String(255)),
    Column("version_number", Integer, nullable=False, server_default="0"),
)

# Read model table - not mapped to domain entity
# Following Cosmic Python pattern: define in metadata for SQLAlchemy awareness
metrics = Table(
    "metrics",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", String(255)),
    Column("pathogen_code", String(255)),
    Column("pathogen_description", String(255)),
    Column("report_timestamp", String(255)),
    Column("created_at", DateTime),
)

def start_mappers():
    logger.info("Starting mappers")
    mapper_registry.map_imperatively(domain.LabDataProduct, products)

@event.listens_for(domain.LabDataProduct, "load")
def receive_load(product, _):
    product.events = []