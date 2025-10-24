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
from shared.domain import domain

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 pattern: use registry
mapper_registry = registry()
metadata = mapper_registry.metadata

patients = Table(
    "patients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", String(255), unique=True, nullable=False),
    Column("ahv_number", String(255), unique=True, nullable=False),
    Column("family_name", String(255)),
    Column("given_name", String(255)),
    Column("gender", String(255)),
    Column("birthdate", String(255)),
    Column("canton", String(2)),
)

def start_mappers():
    logger.info("Starting mappers")
    mapper_registry.map_imperatively(
        domain.PatientRecord, 
        patients,
        properties={
            # SQLAlchemy will handle auto-increment for id automatically
            'id': patients.c.id,
            'patient_id': patients.c.patient_id,
            'ahv_number': patients.c.ahv_number,
            'family_name': patients.c.family_name,
            'given_name': patients.c.given_name,
            'gender': patients.c.gender,
            'birthdate': patients.c.birthdate,
            'canton': patients.c.canton,
        }
    )