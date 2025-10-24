import logging
from sqlalchemy import (
    Table,
    MetaData,
    Column,
    Integer,
    String,
    Date,
    ForeignKey,
    event,
)
from sqlalchemy.orm import registry
from case.domain import domain


logger = logging.getLogger(__name__)

mapper_registry = registry()
metadata = mapper_registry.metadata

cases = Table(
    "cases",
    metadata,
    Column("case_id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", String(255), nullable=False),
    Column("case_date", String(255)),
    Column("case_class", String(255)),
    Column("case_status", String(255)),
    Column("pathogen", String(255)),
    Column("canton", String(2)),
)

case_to_products = Table(
    "case_to_products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", String(255), nullable=False),
    Column("product_id", String(255), nullable=False),
)

def start_mappers():
    logger.info("Starting mappers")
    
    mapper_registry.map_imperatively(domain.CaseRecord, cases)
    mapper_registry.map_imperatively(domain.CaseToProductRecord, case_to_products)
    