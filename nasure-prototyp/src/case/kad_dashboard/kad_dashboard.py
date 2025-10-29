import streamlit as st
import pandas as pd
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

api_base_url = os.getenv("CASE_API_URL", "http://case-mgmt-api:8003")
    

# Configure page
st.set_page_config(
    page_title="NASURE Case Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'cached_data' not in st.session_state:
    st.session_state.cached_data = None
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'clear_filters' not in st.session_state:
    st.session_state.clear_filters = False
if 'status_filter' not in st.session_state:
    st.session_state.status_filter = "not_closed"
if 'canton_filter' not in st.session_state:
    st.session_state.canton_filter = "All"
if 'patient_id_filter' not in st.session_state:
    st.session_state.patient_id_filter = ""
if 'pathogen_code_filter' not in st.session_state:
    st.session_state.pathogen_code_filter = ""
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""

@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_all_cases(api_url: str, page_size: int = 100) -> Dict:
    """Fetch ALL cases from the case management API (no server-side filtering)"""
    try:
        params = {
            "page_size": page_size,
            "page": 1,
            "status": "all"  # Fetch all cases regardless of status
        }
        
        # Use httpx.Client with context manager
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{api_url}/api/v1/cases", params=params)
            
            if response.status_code == 404:
                st.error("❌ Case API endpoint not found")
                return {"cases": [], "total_count": 0}
                
            response.raise_for_status()
            return response.json()
        
    except httpx.RequestError as e:
        st.error(f"❌ Connection Error: {e}")
        return {"cases": [], "total_count": 0}
    except httpx.HTTPStatusError as e:
        st.error(f"❌ HTTP Error: {e.response.status_code}")
        return {"cases": [], "total_count": 0}
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")
        return {"cases": [], "total_count": 0}

def fetch_case_products(api_url: str, case_id: str) -> Optional[List[Dict]]:
    """Fetch all products linked to a specific case"""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{api_url}/api/v1/cases/{case_id}/products")
            
            if response.status_code == 200:
                data = response.json()
                return data.get("products", [])
            elif response.status_code == 404:
                st.warning(f"⚠️ No products found for case {case_id}")
                return []
            else:
                response.raise_for_status()
                
    except httpx.RequestError as e:
        st.error(f"❌ Error fetching case products: {e}")
        return []
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return []


def format_case_data(cases_data: Dict) -> pd.DataFrame:
    """Convert API response to pandas DataFrame"""
    if not cases_data.get("cases"):
        return pd.DataFrame()
    
    cases = cases_data["cases"]
    df = pd.DataFrame(cases)
    
    # Format datetime columns
    if 'lab_timestamp' in df.columns:
        try:
            df['lab_timestamp'] = pd.to_datetime(df['lab_timestamp'], format='ISO8601', errors='coerce')
            df['lab_date'] = df['lab_timestamp'].dt.date
            df['lab_time'] = df['lab_timestamp'].dt.time
        except Exception as e:
            st.warning(f"⚠️ Error parsing lab_timestamp: {e}")
            # Fallback: try without format specification
            try:
                df['lab_timestamp'] = pd.to_datetime(df['lab_timestamp'], errors='coerce')
                df['lab_date'] = df['lab_timestamp'].dt.date
                df['lab_time'] = df['lab_timestamp'].dt.time
            except Exception as e2:
                st.error(f"❌ Failed to parse lab_timestamp: {e2}")
                # Keep original string values
                df['lab_date'] = df['lab_timestamp']
                df['lab_time'] = None


    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['created_date'] = df['created_at'].dt.date
    
    # Add age in days
    if 'lab_timestamp' in df.columns:
        df['age_days'] = (datetime.now() - df['lab_timestamp']).dt.days
    
    return df

def apply_filters(df: pd.DataFrame, status_filter: str, canton_filter: Optional[str], 
                 patient_id_filter: str, pathogen_code_filter: str, search_term: str) -> pd.DataFrame:
    """Apply client-side filters to the dataframe with safe column checking"""
    df_filtered = df.copy()
    
    # Status filter - check if column exists
    if status_filter != "All" and 'status' in df_filtered.columns:
        if status_filter == "not_closed":
            df_filtered = df_filtered[~df_filtered['status'].isin(['abgeschlossen', 'archiviert'])]
        else:
            df_filtered = df_filtered[df_filtered['status'] == status_filter]
    
    # Canton filter - check if column exists
    if canton_filter and canton_filter != "All" and 'canton' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['canton'] == canton_filter]
    
    # Patient ID filter - check if column exists
    if patient_id_filter and 'patient_id' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['patient_id'].str.contains(patient_id_filter, case=False, na=False)]
    
    # Pathogen code filter - check if column exists
    if pathogen_code_filter and 'pathogen_code' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['pathogen_code'].str.contains(pathogen_code_filter, case=False, na=False)]
    
    # Search term (searches across all columns) - check if dataframe is not empty
    if search_term and not df_filtered.empty:
        try:
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            df_filtered = df_filtered[mask] if isinstance(mask, pd.Series) else df_filtered
        except Exception as e:
            # If search fails, log and return unfiltered data
            st.warning(f"Search failed: {e}")
    
    return df_filtered

def create_summary_metrics(df: pd.DataFrame, df_filtered: pd.DataFrame):
    """Create summary metric cards showing both total and filtered counts"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_cases = len(df)
        filtered_cases = len(df_filtered)
        delta = f"{filtered_cases}/{total_cases}" if total_cases != filtered_cases else None
        st.metric("📋 Total Cases", filtered_cases, delta=delta)
    
    with col2:
        if 'status' in df_filtered.columns:
            new_cases = len(df_filtered[df_filtered['status'] == 'neu'])
            total_new = len(df[df['status'] == 'neu']) if 'status' in df.columns else 0
            delta = f"of {total_new}" if new_cases != total_new else None
            st.metric("🆕 New Cases", new_cases, delta=delta)
        else:
            st.metric("🆕 New Cases", 0)
    
    with col3:
        if 'age_days' in df_filtered.columns and not df_filtered.empty:
            avg_age = df_filtered['age_days'].mean()
            st.metric("📅 Avg Age (days)", f"{avg_age:.1f}")
        else:
            st.metric("📅 Avg Age (days)", "0.0")
    
    with col4:
        if 'pathogen_code' in df_filtered.columns:
            unique_pathogens = df_filtered['pathogen_code'].nunique()
            total_unique = df['pathogen_code'].nunique() if 'pathogen_code' in df.columns else 0
            delta = f"of {total_unique}" if unique_pathogens != total_unique else None
            st.metric("🦠 Unique Pathogens", unique_pathogens, delta=delta)
        else:
            st.metric("🦠 Unique Pathogens", 0)

def authenticate_user(username: str, password: str) -> bool:
    """Simple authentication - replace with proper auth later"""
    return username == "admin" and password == "admin"

def fetch_patient_data(patient_id: str) -> Optional[Dict]:
    """Fetch patient data from patient service API"""
    if not st.session_state.authenticated:
        return None
        
    try:
        patient_service_url = os.getenv("PATIENT_SERVICE_URL", "http://patient-service-api:8002")
        
        with httpx.Client(timeout=10.0) as client:
            # Use the patient lookup endpoint
            response = client.get(f"{patient_service_url}/api/v1/patient/{patient_id}")
            
            if response.status_code == 404:
                st.warning(f"⚠️ Patient {patient_id} not found")
                return None
            elif response.status_code == 403:
                st.error("❌ Access denied - insufficient permissions")
                return None
                
            response.raise_for_status()
            return response.json()
            
    except httpx.RequestError as e:
        st.error(f"❌ Error connecting to patient service: {e}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"❌ Patient service error: {e.response.status_code}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error fetching patient data: {e}")
        return None
    
# --- Main Dashboard ---

st.title("🏥 NASURE Case Management Dashboard")


# --- Sidebar ---

# Auto-refresh settings
st.sidebar.subheader("🔄 Data Refresh ")
auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=st.session_state.auto_refresh)
if auto_refresh:
    refresh_interval = st.sidebar.selectbox(
        "Refresh Interval", 
        [10, 30, 60, 120], 
        index=1,
        format_func=lambda x: f"{x} seconds"
    )
    st.session_state.auto_refresh = True
else:
    st.session_state.auto_refresh = False

# Manual refresh button
if st.sidebar.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# Authentication Section
st.sidebar.subheader("🔐 Authentication")

if not st.session_state.authenticated:
    # Login form
    with st.sidebar.form("login_form"):
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password", placeholder="admin")
        login_button = st.form_submit_button("🔑 Login")
        
        if login_button:
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.sidebar.success("✅ Authentication successful!")
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid credentials")
else:
    # Show logged in user
    st.sidebar.success(f"✅ Logged in as: {st.session_state.username}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f"created with ❤️  \n© by NASURE team 2025")

# --- Main Content ---

# Auto-refresh logic
if auto_refresh and st.session_state.last_refresh:
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh >= refresh_interval:
        st.cache_data.clear()
        st.rerun()

# Fetch data
with st.spinner("🔄 Loading all cases..."):
    cases_data = fetch_all_cases(api_base_url)
    # TODO: if cases_data.get("total_count", 0) > 1000, show warning about missing pagination
    st.session_state.last_refresh = datetime.now()
    st.session_state.cached_data = cases_data
    
# Convert to DataFrame
df_all = format_case_data(cases_data)

# Summary metrics (showing filtered vs total)
df_filtered = df_all.copy()  # Initially, no filters applied
create_summary_metrics(df_all, df_filtered)

# Display last refresh time and total count
if st.session_state.last_refresh:
    total_count = len(df_all)
    st.caption(f"Last refreshed: {st.session_state.last_refresh.strftime('%H:%M:%S')} | Total cases loaded: {total_count}")

# --- Case Table with Interactive Details ---
st.markdown("---")
st.header("📋 Case Details")

# --- CLIENT-SIDE FILTERS ---

# Create filter columns
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    status_options = ["All", "not_closed", "neu", "in Bearbeitung", "abgeschlossen", "archiviert"]
    status_filter = st.selectbox(
        "📊 Case Status", 
        status_options, 
        index=status_options.index(st.session_state.status_filter),
        key="status_select"
    )
    st.session_state.status_filter = status_filter

with filter_col2:
    # Swiss cantons + get unique cantons from data
    base_cantons = ["All", "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR",
                   "JU", "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG",
                   "TI", "UR", "VD", "VS", "ZG", "ZH"]
    
    # Add any additional cantons found in the data
    if 'canton' in df_all.columns:
        data_cantons = df_all['canton'].dropna().unique().tolist()
        all_cantons = base_cantons + [c for c in data_cantons if c not in base_cantons]
    else:
        all_cantons = base_cantons
    
    canton_filter = st.selectbox(
        "🗺️ Canton", 
        all_cantons,
        index=all_cantons.index(st.session_state.canton_filter) if st.session_state.canton_filter in all_cantons else 0,
        key="canton_select"
    )
    st.session_state.canton_filter = canton_filter

with filter_col3:
    patient_id_filter = st.text_input(
        "👤 Patient ID", 
        placeholder="Enter patient ID...",
        value=st.session_state.patient_id_filter,
        key="patient_input"
    )
    st.session_state.patient_id_filter = patient_id_filter

with filter_col4:
    pathogen_code_filter = st.text_input(
        "🦠 Pathogen Code", 
        placeholder="e.g., 31726-3",
        value=st.session_state.pathogen_code_filter,
        key="pathogen_input"
    )
    st.session_state.pathogen_code_filter = pathogen_code_filter

# Global search
search_term = st.text_input(
    "🔍 Search across all fields", 
    placeholder="Search patient ID, pathogen, case ID...",
    value=st.session_state.search_term,
    key="search_input"
)
st.session_state.search_term = search_term

# Clear filters button with actual clearing functionality
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🗑️ Clear All Filters"):
        # Reset all filter session state values
        st.session_state.status_filter = "All"
        st.session_state.canton_filter = "All"
        st.session_state.patient_id_filter = ""
        st.session_state.pathogen_code_filter = ""
        st.session_state.search_term = ""
        st.rerun()

# --- APPLY FILTERS ---
df_filtered = apply_filters(
    df_all, 
    status_filter, 
    canton_filter if canton_filter != "All" else None,
    patient_id_filter, 
    pathogen_code_filter, 
    search_term
)

# --- DISPLAY FILTERED TABLE ---

if not df_filtered.empty:
    # Display filter results
    if len(df_filtered) != len(df_all):
        st.info(f"📊 Showing {len(df_filtered)} of {len(df_all)} cases (filtered)")
    else:
        st.info(f"📊 Showing all {len(df_filtered)} cases")
    
    # Enhanced table with action buttons for each row
    display_columns = [
        'status', 'pathogen_code', 'pathogen_description',  
        'canton', 'lab_date', 'created_date', 'age_days'
    ]
    
    # Only show columns that exist
    available_columns = [col for col in display_columns if col in df_filtered.columns]
    
    if available_columns:
        # Display clickable table
        st.markdown("**Click on a row to view case details:**")
        
        # Sort the DataFrame by a specific column before displaying (e.g., by 'lab_date' descending)
        sort_column = "lab_date"  # Change this to your preferred column
        ascending = True         # Set to True for ascending, False for descending

        if sort_column in df_filtered.columns:
            df_display = df_filtered.sort_values(by=sort_column, ascending=ascending)
        else:
            df_display = df_filtered

        event = st.dataframe(
            df_display[available_columns],
            width='stretch',
            height=500,
            on_select="rerun",  # Enable row selection
            selection_mode="single-row",  # Allow only single row selection
            column_config={
            "status": st.column_config.TextColumn("Status", width="small"),
            "pathogen_code": st.column_config.TextColumn("Pathogen Code", width="small"),
            "pathogen_description": st.column_config.TextColumn("Pathogen", width="large"),
            "canton": st.column_config.TextColumn("Canton", width="small"),
            "lab_date": st.column_config.DateColumn("Lab Date", width="small"),
            "created_date": st.column_config.DateColumn("Created", width="small"),
            "age_days": st.column_config.NumberColumn("Age (days)", width="small")
            }
        )
        
        # Handle row selection
        if event.selection.rows:  # If a row is selected
            selected_row_index = event.selection.rows[0]  # Get first selected row index
            
            # Get the selected case data
            if selected_row_index < len(df_display):
                case_row = df_display.iloc[selected_row_index].to_dict()
                selected_case_id = case_row.get('case_id', 'Unknown')
                
                # Clear patient data when a different case is selected
                if 'current_selected_case' not in st.session_state or st.session_state.current_selected_case != selected_case_id:
                    # Clear all patient data from session state
                    keys_to_remove = [key for key in st.session_state.keys() if key.startswith('patient_data_')]
                    for key in keys_to_remove:
                        del st.session_state[key]
                    
                    # Store the current selected case ID
                    st.session_state.current_selected_case = selected_case_id

                # Case Detail Actions
                st.markdown("---")
                st.subheader(f"🔍 Case Details")
                
                with st.expander(f"📋 Selected Case: {selected_case_id}", expanded=True):
                    # Display case information in a nice format
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Case Information**")
                        
                        # Enhanced patient information
                        status = case_row.get('status')
                        if status == 'neu':
                            st.markdown("**Case Status:** :blue-badge[neu]")
                        elif status == 'in Bearbeitung':
                            st.markdown("**Case Status:** :orange-badge[in Bearbeitung]")
                        elif status == 'abgeschlossen':
                            st.markdown("**Case Status:** :green-badge[abgeschlossen]")
                        
                        st.write(f"**Canton:** {case_row.get('canton', 'N/A')}")
                   
                    with col2:
                        st.write("**Pathogen Information**")
                        st.write(f"**Code:** {case_row.get('pathogen_code', 'N/A')}")
                        st.write(f"**Description:** {case_row.get('pathogen_description', 'N/A')}")
                        st.write(f"**Case Class:** {case_row.get('case_class', 'N/A')}")
                    
                    with col3:
                        st.write("**Timeline**")
                        st.write(f"**Lab Date:** {case_row.get('lab_date', 'N/A')}")
                        st.write(f"**Created:** {case_row.get('created_date', 'N/A')}")
                        st.write(f"**Age:** {case_row.get('age_days', 'N/A')} days")
                    
                    st.markdown("---")
                    st.write("**Patient Data**")
                    patient_id = case_row.get('patient_id', 'N/A')
                    
                    # Show patient data if authenticated
                    if st.session_state.authenticated and patient_id != 'N/A':
                    
                        if st.button("👤 Fetch Patient Data", key=f"fetch_patient_{selected_case_id}"):
                            with st.spinner("🔄 Fetching patient data..."):
                                patient_data = fetch_patient_data(patient_id)
                                
                                if patient_data:
                                    st.session_state[f'patient_data_{patient_id}'] = patient_data
                                    st.success("✅ Patient data fetched successfully!")
                        
                        # Display patient data if available
                        if f'patient_data_{patient_id}' in st.session_state:
                            patient_info = st.session_state[f'patient_data_{patient_id}']
                            
                            col_pat1, col_pat2= st.columns(2)
                            with col_pat1:
                                st.write(f"**Patient ID:** {patient_id}")
                                st.write(f"**Family Name:** {patient_info.get('family_name', 'N/A')}")
                                st.write(f"**Given Name:** {patient_info.get('given_name', 'N/A')}") 

                            with col_pat2:
                                st.write(f"**AHV Number:** {patient_info.get('ahv_number', 'N/A')}")
                                st.write(f"**Birthdate:** {patient_info.get('birthdate', 'N/A')}")
                                st.write(f"**Canton of residence:** {case_row.get('canton', 'N/A')}")
                               
                            # Raw patient data
                            with st.expander("🔧 Raw Patient Data"):
                                st.json(patient_info)
                        else:
                            col_pat1, col_pat2= st.columns(2)
                            with col_pat1:
                                st.write(f"**Patient ID:** {patient_id}")
                                st.write(f"**Family Name:** *****")
                                st.write(f"**Given Name:** *****") 

                            with col_pat2:
                                st.write(f"**AHV Number:** *****" )
                                st.write(f"**Birthdate:** *****" )
                                st.write(f"**Canton of residence:** {case_row.get('canton', 'N/A')}")
                    
                    elif not st.session_state.authenticated:
                        st.info("🔐 Login required to view patient data")
                        col_pat1, col_pat2= st.columns(2)
                        with col_pat1:
                            st.write(f"**Patient ID:** {patient_id}")
                            st.write(f"**Family Name:** *****")
                            st.write(f"**Given Name:** *****") 

                        with col_pat2:
                            st.write(f"**AHV Number:** *****" )
                            st.write(f"**Birthdate:** *****" )
                            st.write(f"**Canton of residence:** {case_row.get('canton', 'N/A')}")

                    # --- Linked Lab and Clinical Reports ---

                    st.markdown("---")
                    st.write("**📄 Linked Lab and Clinical Reports**")
                    
                    # Auto-load products when case is selected
                                                
                    with st.spinner("🔄 Loading linked reports..."):                         

                        case_products = fetch_case_products(api_base_url, selected_case_id)
                        st.session_state[f'case_products_{selected_case_id}'] = case_products
                    
                    products = st.session_state.get(f'case_products_{selected_case_id}', [])
                    
                    if products:
                        st.write(f"**Found {len(products)} linked reports:**")
                        
                        for i, product in enumerate(products):
                            relationship_icon = "🎯" if product.get('is_original') else "🔗"
                            relationship_text = "Original Report" if product.get('is_original') else "Additional Report"
                            
                            with st.expander(f"{relationship_icon} {relationship_text}: {product.get('product_id', 'Unknown')}", expanded=False):
                                prod_col1, prod_col2 = st.columns(2)
                                
                                with prod_col1:
                                    st.write(f"**Report ID:** {product.get('product_id', 'N/A')}")
                                    st.write(f"**Relationship:** {relationship_text}")
                                    st.write(f"**Linked At:** {product.get('linked_at', 'N/A')}")
                                
                                with prod_col2:
                                    if st.button(f"🔍 View Report Details", key=f"view_product_{i}_{selected_case_id}"):
                                        # Here you could fetch detailed product info from lab-dp-api
                                        st.info("🚧 Product details view coming soon...")                                   

                    else:
                        st.info("ℹ️ No reports linked to this case")
                                       
                    # Action buttons
                    st.markdown("---")
                    st.markdown("**Actions:**")
                    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                    
                    with action_col1:
                        if st.button("✅ Mark Processed", key=f"process_{selected_case_id}"):
                            st.info("🚧 Action functionality coming soon...")
                            # if update_case_status(api_base_url, selected_case_id, "in Bearbeitung"):
                            #     st.cache_data.clear()  # Refresh data
                            #     st.rerun()
                    
                    with action_col2:
                        if st.button("🔄 Refresh Case", key=f"refresh_{selected_case_id}"):
                            st.info("🚧 Refresh functionality coming soon...")
                            # detailed_case = fetch_single_case(api_base_url, selected_case_id)
                            # if detailed_case:
                            #     st.success("✅ Case refreshed")
                            #     st.json(detailed_case)
                    
                    with action_col3:
                        if st.button("📋 View Lab Data", key=f"lab_{selected_case_id}"):
                            # Link to lab data product
                            lab_dp_url = "http://lab-dp-api:8001"
                            product_id = case_row.get('product_id', 'unknown')
                            st.info(f"🔗 Lab Data URL: {lab_dp_url}/api/v1/data-product/{product_id}")
                            st.write(f"Product ID: {product_id}")
                    
                    with action_col4:
                        if st.button("🏁 Close Case", key=f"close_{selected_case_id}"):
                            st.info("🚧 Close case functionality coming soon...")
                            # if update_case_status(api_base_url, selected_case_id, "abgeschlossen"):
                            #     st.cache_data.clear()  # Refresh data
                            #     st.rerun()
        
    else:
        # Fallback: show all available columns
        st.dataframe(df_filtered, width='stretch', height=400)

        # Export functionality
        st.subheader("💾 Export Data")
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_filtered.to_csv(index=False)
            st.download_button(
                "📄 Download as CSV",
                csv_data,
                file_name=f"cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = df_filtered.to_json(orient='records', date_format='iso')
            st.download_button(
                "📋 Download as JSON",
                json_data,
                file_name=f"cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

else:
    st.info("📭 No cases found with current filters")
    if len(df_all) > 0:
        st.info(f"💡 Try adjusting your filters. Total available cases: {len(df_all)}")