CREATE SCHEMA IF NOT EXISTS patient;

CREATE TABLE IF NOT EXISTS patient.patients (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      UUID        NOT NULL,
    ahv_number      VARCHAR(20) NOT NULL,
    family_name     VARCHAR(200) NOT NULL,
    given_name      VARCHAR(200) NOT NULL,
    gender          VARCHAR(10)  NOT NULL CHECK (gender IN ('male', 'female', 'other', 'unknown')),
    birthdate       DATE NOT NULL,
    canton          VARCHAR(2)   NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_patients_ahv ON patient.patients (ahv_number);
CREATE UNIQUE INDEX IF NOT EXISTS ux_patients_pid ON patient.patients (patient_id);

CREATE OR REPLACE FUNCTION patient.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_patients_updated ON patient.patients;
CREATE TRIGGER trg_patients_updated
BEFORE UPDATE ON patient.patients
FOR EACH ROW EXECUTE PROCEDURE patient.set_updated_at();