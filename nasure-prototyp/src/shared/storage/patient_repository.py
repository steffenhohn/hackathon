"""
PostgreSQL Repository for Patients
Stores Patient data with unique UUIDs and AHV numbers
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import psycopg  # psycopg3
import logging

logger = logging.getLogger(__name__)

@dataclass
class PatientRecord:
    patient_id: str           # UUID4 as String
    ahv_number: str           # normalised (numbers only)
    family_name: str
    given_name: str
    gender: str               # 'male' | 'female' | 'other' | 'unknown'
    birthdate: str            # 'YYYY-MM-DD'
    canton: str               # 2 letter canton code

class PatientRepository:
    def __init__(self, conn_str: str):
        self._conn_str = conn_str

    def get_patient_id_by_ahv(self, ahv: str) -> Optional[str]:
        """Return the patient_id if a record with this AHV exists, else None."""
        try:
            with psycopg.connect(self._conn_str) as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT patient_id
                    FROM person.persons
                    WHERE ahv_number = %s
                """, (ahv,))
                row = cur.fetchone()
                return str(row[0]) if row else None
        except psycopg.Error as e:
            logger.error(f"Database error fetching patient_id with AHV {ahv}: {e}")
            return None

    def get_patient_details_by_patient_id(self, patient_id: str) -> Optional[PatientRecord]:
        """
        Get patient details by patient_id
        Returns: PatientRecord or None
        """
        try:
            with psycopg.connect(self._conn_str) as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT id, patient_id, ahv_number, family_name, given_name, gender, birthdate, canton
                    FROM patient.patients
                    WHERE patient_id = %s
                """, (patient_id,))
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d.name for d in cur.description]
                data = dict(zip(cols, row))
                return PatientRecord(
                    patient_id=data["patient_id"],
                    ahv_number=data["ahv_number"],
                    family_name=data["family_name"],
                    given_name=data["given_name"],
                    gender=data["gender"],
                    birthdate=str(data["birthdate"]),
                    canton=data["canton"],
                )
        except psycopg.Error as e:
            logger.error(f"Database error fetching patient_id {patient_id}: {e}")
            return None

    def upsert_patient_by_ahv(self, p: PatientRecord) -> Tuple[str, bool]:
        """
        Idempotent:
        - Insert with new UUID4 for new AHV
        - On conflict (ahv_number), replace patient data but keep patient_id unchanged.,
        Returns: (patient_id, inserted)
        """
        try:
            with psycopg.connect(self._conn_str) as conn, conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO patient.patients
                        (patient_id, ahv_number, family_name, given_name, gender, birthdate, canton)
                    VALUES
                        (%(patient_id)s, %(ahv_number)s, %(family_name)s, %(given_name)s, %(gender)s, %(birthdate)s, %(canton)s)
                    ON CONFLICT (ahv_number) DO UPDATE SET
                        family_name = EXCLUDED.family_name,
                        given_name  = EXCLUDED.given_name,
                        gender      = EXCLUDED.gender,
                        birthdate   = EXCLUDED.birthdate,
                        canton      = EXCLUDED.canton
                    RETURNING patient_id, (xmax = 0) AS inserted; -- True if inserted, False if updated (PostgreSQL system column trick)
                """, {
                    "patient_id":  p.patient_id,
                    "ahv_number":  p.ahv_number,
                    "family_name": p.family_name,
                    "given_name":  p.given_name,
                    "gender":      p.gender,
                    "birthdate":   p.birthdate,
                    "canton":      p.canton,
                })
                patient_id, inserted = cur.fetchone()
            return str(patient_id), bool(inserted)
        except psycopg.Error as e:
            logger.error(f"Database error upserting patient AHV {p.ahv_number}: {e}")
            return "", False