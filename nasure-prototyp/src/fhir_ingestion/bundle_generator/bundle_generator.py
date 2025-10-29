import json
import streamlit as st
import requests
from datetime import date, datetime
from copy import deepcopy
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="FHIR Bundle Generator",
    page_icon="📃",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'bundle_created' not in st.session_state:
    st.session_state.bundle_created = False
if 'current_bundle' not in st.session_state:
    st.session_state.current_bundle = None

# Load your base example as a template
bundle_path = Path("examples/ch_elm_bundles") / "legionella_1.json"

@st.cache_data
def load_template():
    """Load FHIR template with error handling"""
    try:
        with open(bundle_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Template nicht gefunden: {bundle_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Template JSON fehlerhaft: {e}")
        st.stop()

template = load_template()

# Define available pathogens
pathogens = {
    "Bacillus anthracis": {
        "code": "31726-3",
        "display": "Bacillus anthracis [Presence] in Specimen by Organism specific culture"
    },
    "Legionella pneumophila": {
        "code": "32781-7", 
        "display": "Legionella pneumophila [Presence] in Specimen by Organism specific culture"
    },
    "Plasmodium": {
        "code": "70568-1",
        "display": "Plasmodium sp identified in Blood by Light microscopy"
    },
    "Gonorrhoeae": {
        "code": "697-3",
        "display": "Neisseria gonorrhoeae [Presence] in Urethra by Organism specific culture"
    }
}

def send_to_fhir_api(bundle_data, api_url, timeout=30):
    """Send FHIR bundle to ingestion API"""
    try:
      
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        st.info(f"📤 Sende an: {api_url}")
        
        response = requests.post(
            api_url,
            json=bundle_data,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200 or response.status_code == 201:
            return True, response.json()
        else:
            return False, {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except requests.exceptions.ConnectionError:
        return False, {"error": "Verbindungsfehler", "message": f"Kann API unter {api_url} nicht erreichen"}
    except requests.exceptions.Timeout:
        return False, {"error": "Timeout", "message": f"API antwortet nicht innerhalb von {timeout} Sekunden"}
    except Exception as e:
        return False, {"error": "Unbekannter Fehler", "message": str(e)}

def create_bundle():
    """Create FHIR bundle from form data"""
    bundle = deepcopy(template)

    # --- Update Patient ---
    for entry in bundle["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            patient = entry["resource"]
            patient["id"] = pat_ahv
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
            
            # Set interpretation code
            interpretation_map = {
                "positive": "POS",
                "negative": "NEG",
                "indeterminate": "IND"
            }
            obs["interpretation"][0]["coding"][0]["code"] = interpretation_map.get(
                obs_value.lower(), "IND"
            )

    # --- Update timestamp ---
    bundle["timestamp"] = datetime.now().isoformat()
    
    return bundle

# --- Streamlit UI ---

st.title("FHIR Bundle Generator (CH-ELM)")

# --- Sidebar ---

# API Configuration Section
st.sidebar.header("🔗 API Konfiguration")
api_base_url = st.sidebar.text_input(
    "FHIR Bundle Ingestion API Host", 
    "http://localhost:8000"  # Default to your FHIR ingestion service
)
api_fhir_endpoint = st.sidebar.text_input(
    "FHIR Bundle Ingestion API Endpoint", 
    "/api/v1/fhir/ingest"  
)
api_url = f"{api_base_url.rstrip('/')}{api_fhir_endpoint}"
api_timeout = st.sidebar.number_input("Timeout (Sekunden)", min_value=5, max_value=60, value=30)

# API Status Check in Sidebar
st.sidebar.subheader("🏥 API Status")

if st.sidebar.button("🔍 Check API"):
    try:
        st.sidebar.info(f"Checking API: {api_base_url}/health")
        response = requests.get(f"{api_base_url}/health", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ API reachable")
        else:
            st.sidebar.warning(f"⚠️ API answers with status {response.status_code}")
    except:
        st.sidebar.error("❌ API not reachable")

st.sidebar.markdown("---")
st.sidebar.markdown(f"created with ❤️  \n© by NASURE team 2025")

# --- Form  ---

st.header("👤 Patientendaten")
pat_ahv = st.text_input("Patient AHV", "759.123.456.78")
pat_family = st.text_input("Familienname", "Muster")
pat_given = st.text_input("Vorname", "Max")
pat_gender = st.selectbox("Geschlecht", ["male", "female", "other", "unknown"])
pat_birth = st.date_input("Geburtsdatum", date(1980, 1, 1))
pat_city = st.text_input("Ort", "Bern")
pat_postcode = st.text_input("PLZ", "3000")
# Swiss cantons (2-letter abbreviations, alphabetic order)
swiss_cantons = [
    "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR",
    "JU", "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG",
    "TI", "UR", "VD", "VS", "ZG", "ZH"
]
pat_canton = st.selectbox("Kanton", swiss_cantons, index=swiss_cantons.index("BE"))

st.header("🧫 Observation")
# User-friendly pathogen selection
selected_pathogen_name = st.selectbox(
    "🦠 Pathogen auswählen",
    list(pathogens.keys()),
    index=1  # Default to Legionella
)

# Get code and description from selection
obs_code = pathogens[selected_pathogen_name]["code"]
obs_display = pathogens[selected_pathogen_name]["display"]

# Show selected values in info boxes
st.info(f"**LOINC Code:** {obs_code}  \n**Pathogen:** {obs_display}")

obs_value = st.selectbox("Resultat", ["Positive", "Negative", "Indeterminate"])
obs_date = st.date_input("Analysedatum", date.today())



st.header("🚀 Action")
# Generate bundle preview

# Track form changes to reset bundle state
# Store current form values
current_form_values = {
    'pat_ahv': pat_ahv,
    'pat_family': pat_family,
    'pat_given': pat_given,
    'pat_gender': pat_gender,
    'pat_birth': pat_birth.isoformat(),
    'pat_city': pat_city,
    'pat_postcode': pat_postcode,
    'pat_canton': pat_canton,
    'selected_pathogen': selected_pathogen_name,
    'obs_value': obs_value,
    'obs_date': obs_date.isoformat()
}

# Check if form has changed since last bundle creation
if 'last_form_values' not in st.session_state:
    st.session_state.last_form_values = {}

# If form values have changed, automatically reset bundle
if (st.session_state.bundle_created and 
    current_form_values != st.session_state.last_form_values):
    
    st.session_state.bundle_created = False
    st.session_state.current_bundle = None
    st.info("🔄 Form entries have changed. Create new FHIR bundle to enable actions.")

# Update stored form values
st.session_state.last_form_values = current_form_values

if st.button("🛠️ Create FHIR Bundle"):

    # Validate required fields
    if not pat_ahv.strip():
        st.error("❌ Patient AHV is required")
        st.stop()

    if not obs_code.strip():
        st.error("❌ LOINC Code is required")
        st.stop()

    # Create bundle
    bundle = create_bundle()
    # Store bundle in session state
    st.session_state.current_bundle = bundle
    st.session_state.bundle_created = True

    st.success("✅ FHIR Bundle created successfully!")

    # Show JSON preview
    with st.expander("👁️ JSON Preview"):
        st.json(bundle)

# Create two columns for side-by-side buttons
col1, col2 = st.columns(2)

# Check if bundle has been created
bundle_available = st.session_state.bundle_created and st.session_state.current_bundle is not None

# First button in left column
with col1:
    if bundle_available:
        json_str = json.dumps(st.session_state.current_bundle, indent=2, ensure_ascii=False)
        download_clicked = st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=f"FHIR_Bundle_{pat_ahv}.json",
            mime="application/json",
            key=f"FHIR_bundle_{pat_ahv}",
            use_container_width=True
        )
    else:
        # Disabled button (visual only)
        st.button(
            "💾 Download JSON", 
            disabled=True, 
            use_container_width=True,
            help="Create a FHIR Bundle first"
        )

# Second button in right column  
with col2:
    if bundle_available:
        send_clicked = st.button("📤 Send to API", use_container_width=True)
    else:
        # Disabled button
        send_clicked = st.button(
            "📤 Send to API", 
            disabled=True, 
            use_container_width=True,
            help="Create a FHIR Bundle first"
        )

# Handle Send to API button (only if bundle is available)
if send_clicked and bundle_available:

    st.subheader("📤 API Ingestion")
    
    with st.spinner("Send to FHIR Ingestion API..."):
        success, result = send_to_fhir_api(st.session_state.current_bundle, api_url, api_timeout)
    
    if success:
        st.success("✅ Successfully sent FHIR bundle to API!")
        
        # Show API response
        with st.expander("📋 API Response"):
            st.json(result)
            
    else:
        st.error(f"❌ API Error: {result['error']}")
        st.error(f"💬 {result['message']}")
