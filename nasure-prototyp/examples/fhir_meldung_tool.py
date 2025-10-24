import json
import streamlit as st
from datetime import date, datetime
from copy import deepcopy

# Load your base example as a template
from pathlib import Path

# Define where your example bundles are stored
bundle_path = Path("ch_elm_bundles") / "LB_beispiel_Gonorrhoe.json"

# Load your base example as a template
with open(bundle_path, "r", encoding="utf-8") as f:
    template = json.load(f)

st.title("FHIR Meldung Generator (CH-ELM)")

st.header("👤 Patientendaten")
pat_id = st.text_input("Patient ID", "Pat-001")
pat_family = st.text_input("Familienname", "Muster")
pat_given = st.text_input("Vorname", "Max")
pat_gender = st.selectbox("Geschlecht", ["male", "female", "other", "unknown"])
pat_birth = st.date_input("Geburtsdatum", date(1980, 1, 1))
pat_city = st.text_input("Ort", "Bern")
pat_postcode = st.text_input("PLZ", "3000")
pat_canton = st.text_input("Kanton", "BE")

st.header("🧫 Observation")
obs_code = st.text_input("LOINC Code", "697-3")
obs_display = st.text_input("LOINC Display", "Neisseria gonorrhoeae [Presence] in Urethra by Organism specific culture")
obs_value = st.selectbox("Resultat", ["Positive", "Negative", "Indeterminate"])
obs_date = st.date_input("Analysedatum", date.today())

if st.button("Generate JSON"):
    bundle = deepcopy(template)

    # --- Update Patient ---
    for entry in bundle["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            patient = entry["resource"]
            patient["id"] = pat_id
            patient["name"][0]["family"] = pat_family
            patient["name"][0]["given"] = [pat_given]
            patient["gender"] = pat_gender
            patient["birthDate"] = pat_birth.isoformat()
            patient["address"][0]["city"] = pat_city
            patient["address"][0]["postalCode"] = pat_postcode
            patient["address"][0]["state"] = pat_canton

    # --- Update Observation ---
    for entry in bundle["entry"]:
        if entry["resource"]["resourceType"] == "Observation":
            obs = entry["resource"]
            obs["effectiveDateTime"] = obs_date.isoformat()
            obs["code"]["coding"][0]["code"] = obs_code
            obs["code"]["coding"][0]["display"] = obs_display
            obs["valueCodeableConcept"]["coding"][0]["display"] = obs_value
            if obs_value.lower() == "positive":
                obs["interpretation"][0]["coding"][0]["code"] = "POS"
            elif obs_value.lower() == "negative":
                obs["interpretation"][0]["coding"][0]["code"] = "NEG"
            else:
                obs["interpretation"][0]["coding"][0]["code"] = "IND"

    # --- Update timestamp ---
    bundle["timestamp"] = datetime.now().isoformat()

    # --- Prepare file ---
    file_name = f"FHIR_Meldung_{pat_id}.json"
    output_path = Path("ch_elm_bundles") / file_name

    # Write file to ch_elm_bundles folder
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(bundle, out, indent=2, ensure_ascii=False)

    st.success(f"FHIR Meldung gespeichert unter: {output_path}")

    # Offer browser download too
    json_str = json.dumps(bundle, indent=2, ensure_ascii=False)
    st.download_button(
        label="⬇️ Download FHIR Meldung JSON",
        data=json_str,
        file_name=file_name,
        mime="application/json"
    )

    st.json(bundle)

    bundle = deepcopy(template)

    # --- Update Patient ---
    for entry in bundle["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            patient = entry["resource"]
            patient["id"] = pat_id
            patient["name"][0]["family"] = pat_family
            patient["name"][0]["given"] = [pat_given]
            patient["gender"] = pat_gender
            patient["birthDate"] = pat_birth.isoformat()
            patient["address"][0]["city"] = pat_city
            patient["address"][0]["postalCode"] = pat_postcode
            patient["address"][0]["state"] = pat_canton

    # --- Update Observation ---
    for entry in bundle["entry"]:
        if entry["resource"]["resourceType"] == "Observation":
            obs = entry["resource"]
            obs["effectiveDateTime"] = obs_date.isoformat()
            obs["code"]["coding"][0]["code"] = obs_code
            obs["code"]["coding"][0]["display"] = obs_display
            obs["valueCodeableConcept"]["coding"][0]["display"] = obs_value
            if obs_value.lower() == "positive":
                obs["interpretation"][0]["coding"][0]["code"] = "POS"
            elif obs_value.lower() == "negative":
                obs["interpretation"][0]["coding"][0]["code"] = "NEG"
            else:
                obs["interpretation"][0]["coding"][0]["code"] = "IND"

    # Update timestamp
    bundle["timestamp"] = datetime.now().isoformat()

    # Output
    json_str = json.dumps(bundle, indent=2, ensure_ascii=False)
    st.download_button(
        label="⬇️ Download FHIR Meldung JSON",
        data=json_str,
        file_name=f"FHIR_Meldung_{pat_id}.json",
        mime="application/json"
    )

    st.success("FHIR Meldung erfolgreich erstellt!")
    st.json(bundle)


