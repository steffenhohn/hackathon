import json
import streamlit as st
from datetime import date, datetime
from pathlib import Path
from copy import deepcopy

# Define the base example location
bundle_path = Path("ch_elm_bundles") / "KB_beispiel_Gonorrhoe.json"

# Try loading the base template
try:
    with open(bundle_path, "r", encoding="utf-8") as f:
        template = json.load(f)
except FileNotFoundError:
    st.error(f"Template file not found: {bundle_path}")
    st.stop()

st.title("FHIR Meldung Generator (Klinische Befunde – CH-ELM)")

# ---------------- Patient data ----------------
st.header("👤 Patientendaten")
pat_id = st.text_input("Patient ID", "Pat-001")
pat_family = st.text_input("Familienname", "Muster")
pat_given = st.text_input("Vorname", "Max")
pat_gender = st.selectbox("Geschlecht", ["male", "female", "other", "unknown"])
pat_birth = st.date_input("Geburtsdatum", date(1980, 1, 1))
pat_city = st.text_input("Ort", "Bern")
pat_postcode = st.text_input("PLZ", "3000")
pat_canton = st.text_input("Kanton", "BE")

# ---------------- Condition data ----------------
st.header("🏥 Klinische Befunde (Condition)")
cond_code = st.text_input("SNOMED Code", "15628003")
cond_display = st.text_input("SNOMED Display", "Gonorrhoe")
cond_status = st.selectbox("Klinischer Status", ["active", "inactive", "resolved"])
cond_confirm = st.selectbox("Verifikation", ["confirmed", "unconfirmed"])
cond_onset = st.date_input("Onset Datum", date.today())
cond_evidence = st.text_input("Befunde (SNOMED Display)", "Urethritis")
cond_evidence_code = st.text_input("Befunde (SNOMED Code)", "31822004")

# ---------------- Generate Button ----------------
if st.button("Generate JSON"):
    bundle = deepcopy(template)

    # --- Update Patient ---
    for entry in bundle["entry"]:
        if entry.get("resource", {}).get("resourceType") == "Patient":
            patient = entry["resource"]
            patient["id"] = pat_id
            patient["name"][0]["family"] = pat_family
            patient["name"][0]["given"] = [pat_given]
            patient["gender"] = pat_gender
            patient["birthDate"] = pat_birth.isoformat()
            patient["address"][0]["city"] = pat_city
            patient["address"][0]["postalCode"] = pat_postcode
            patient["address"][0]["state"] = pat_canton

    # --- Update Condition ---
    for entry in bundle["entry"]:
        if entry.get("resource", {}).get("resourceType") == "Condition":
            cond = entry["resource"]
            cond["code"]["coding"][0]["code"] = cond_code
            cond["code"]["coding"][0]["display"] = cond_display
            cond["clinicalStatus"]["coding"][0]["code"] = cond_status
            cond["verificationStatus"]["coding"][0]["code"] = cond_confirm
            cond["onsetDateTime"] = cond_onset.isoformat()
            cond["evidence"][0]["code"][0]["coding"][0]["display"] = cond_evidence
            cond["evidence"][0]["code"][0]["coding"][0]["code"] = cond_evidence_code
            cond["subject"]["reference"] = f"Patient/{pat_id}"

    # --- Update timestamp ---
    bundle["timestamp"] = datetime.now().isoformat()

    # --- Prepare file path ---
    file_name = f"FHIR_KB_Meldung_{pat_id}.json"
    output_path = Path("ch_elm_bundles") / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Save locally ---
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(bundle, out, indent=2, ensure_ascii=False)

    st.success(f"FHIR Meldung gespeichert unter: {output_path}")

    # --- Provide download button ---
    json_str = json.dumps(bundle, indent=2, ensure_ascii=False)
    st.download_button(
        label="⬇️ Download FHIR Meldung JSON",
        data=json_str,
        file_name=file_name,
        mime="application/json",
        key=f"download_{pat_id}"
    )

    st.json(bundle)

