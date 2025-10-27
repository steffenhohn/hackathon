import streamlit as st
import pandas as pd
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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

@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_cases(api_url: str, status_filter: str = "not_closed", 
                patient_id: str = None, pathogen_code: str = None, 
                canton: str = None, page_size: int = 100) -> Dict:
    """Fetch cases from the case management API"""
    try:
        params = {
            "page_size": page_size,
            "page": 1,
            "status": status_filter
        }
        
        # Add optional filters
        if patient_id:
            params["patient_id"] = patient_id
        if pathogen_code:
            params["pathogen_code"] = pathogen_code
        if canton:
            params["canton"] = canton
        
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

def format_case_data(cases_data: Dict) -> pd.DataFrame:
    """Convert API response to pandas DataFrame"""
    if not cases_data.get("cases"):
        return pd.DataFrame()
    
    cases = cases_data["cases"]
    df = pd.DataFrame(cases)
    
    # Format datetime columns
    if 'lab_timestamp' in df.columns:
        df['lab_timestamp'] = pd.to_datetime(df['lab_timestamp'])
        df['lab_date'] = df['lab_timestamp'].dt.date
        df['lab_time'] = df['lab_timestamp'].dt.time
    
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['created_date'] = df['created_at'].dt.date
    
    # Add age in days
    if 'created_at' in df.columns:
        df['age_days'] = (datetime.now() - df['created_at']).dt.days
    
    return df

def create_summary_metrics(df: pd.DataFrame):
    """Create summary metric cards"""
    if df.empty:
        st.info("📊 No cases to display")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Cases", len(df))
    
    with col2:
        new_cases = len(df[df['status'] == 'neu']) if 'status' in df.columns else 0
        st.metric("🆕 New Cases", new_cases)
    
    with col3:
        avg_age = df['age_days'].mean() if 'age_days' in df.columns else 0
        st.metric("📅 Avg Age (days)", f"{avg_age:.1f}")
    
    with col4:
        unique_pathogens = df['pathogen_code'].nunique() if 'pathogen_code' in df.columns else 0
        st.metric("🦠 Unique Pathogens", unique_pathogens)

# --- Main Dashboard ---

st.title("🏥 NASURE Case Management Dashboard")

# --- Sidebar Configuration ---
st.sidebar.header("🔧 Configuration")

# API Configuration
api_base_url = st.sidebar.text_input(
    "Case API URL", 
    "http://case-mgmt-api:8003"
)

# Auto-refresh settings
st.sidebar.subheader("🔄 Auto Refresh")
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
    st.experimental_rerun()

# --- Filters ---
st.sidebar.header("🔍 Filters")

status_options = ["all", "not_closed", "neu", "in Bearbeitung", "abgeschlossen", "archiviert"]
status_filter = st.sidebar.selectbox("Case Status", status_options, index=1)

# Swiss cantons
swiss_cantons = [
    "All", "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR",
    "JU", "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG",
    "TI", "UR", "VD", "VS", "ZG", "ZH"
]
canton_filter = st.sidebar.selectbox("Canton", swiss_cantons)
canton_filter = None if canton_filter == "All" else canton_filter

patient_id_filter = st.sidebar.text_input("Patient ID (optional)")
pathogen_code_filter = st.sidebar.text_input("Pathogen Code (optional)")

# --- API Status Check ---
st.sidebar.subheader("🌐 API Status")
if st.sidebar.button("🔍 Check API"):
    try:
        response = requests.get(f"{api_base_url}/health", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ API reachable")
            api_info = response.json()
            st.sidebar.json(api_info)
        else:
            st.sidebar.warning(f"⚠️ API status: {response.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ API error: {e}")

# --- Main Content ---

# Auto-refresh logic
if auto_refresh and st.session_state.last_refresh:
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh >= refresh_interval:
        st.cache_data.clear()
        #st.experimental_rerun()

# Fetch data
with st.spinner("🔄 Loading cases..."):
    cases_data = fetch_cases(
        api_base_url,
        status_filter=status_filter,
        patient_id=patient_id_filter if patient_id_filter else None,
        pathogen_code=pathogen_code_filter if pathogen_code_filter else None,
        canton=canton_filter
    )
    
    st.session_state.last_refresh = datetime.now()
    st.session_state.cached_data = cases_data

# Convert to DataFrame
df = format_case_data(cases_data)

# Display last refresh time
if st.session_state.last_refresh:
    st.caption(f"Last refreshed: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

# Summary metrics
create_summary_metrics(df)


# --- Case Table with Interactive Details ---
st.markdown("---")
st.header("📋 Case Details")

if not df.empty:
    # Additional table filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search in table", placeholder="Search patient ID, pathogen...")
    
    with col2:
        # Only show columns that exist in the dataframe
        available_sort_columns = [col for col in ["created_at", "lab_timestamp", "patient_id", "pathogen_code"] if col in df.columns]
        sort_by = st.selectbox("Sort by", available_sort_columns)
    
    with col3:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    # Apply search filter
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        df_filtered = df[mask]
    else:
        df_filtered = df.copy()
    
    # Apply sorting (only if sort column exists)
    if sort_by and sort_by in df_filtered.columns:
        ascending = sort_order == "Ascending"
        df_filtered = df_filtered.sort_values(by=sort_by, ascending=ascending)
    
    # Display results count
    st.info(f"📊 Showing {len(df_filtered)} of {len(df)} cases")
    
    # Enhanced table with action buttons for each row
    display_columns = [
        'case_id', 'patient_id', 'pathogen_description', 'status', 
        'canton', 'lab_date', 'created_date', 'age_days'
    ]
    
    # Only show columns that exist
    available_columns = [col for col in display_columns if col in df_filtered.columns]
    
    if available_columns:
        # Display table
        st.dataframe(
            df_filtered[available_columns],
            use_container_width=True,
            height=400,
            column_config={
                "case_id": st.column_config.TextColumn("Case ID", width="medium"),
                "patient_id": st.column_config.TextColumn("Patient ID", width="medium"),
                "pathogen_description": st.column_config.TextColumn("Pathogen", width="large"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "canton": st.column_config.TextColumn("Canton", width="small"),
                "lab_date": st.column_config.DateColumn("Lab Date", width="small"),
                "created_date": st.column_config.DateColumn("Created", width="small"),
                "age_days": st.column_config.NumberColumn("Age (days)", width="small")
            }
        )
        
        # Case Detail Actions
        st.subheader("🔍 Case Actions")
        
        # Case selection for detailed view
        if 'case_id' in df_filtered.columns:
            case_options = ["Select a case..."] + df_filtered['case_id'].tolist()
            selected_case_id = st.selectbox(
                "Select case for detailed view:", 
                case_options,
                key="case_selector"
            )
            
            if selected_case_id and selected_case_id != "Select a case...":
                # Get case details from the filtered dataframe
                case_row = df_filtered[df_filtered['case_id'] == selected_case_id].iloc[0].to_dict()
                
                with st.expander(f"📋 Case Details: {selected_case_id}", expanded=True):
                    # Display case information in a nice format
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Basic Information**")
                        st.write(f"**Case ID:** {case_row.get('case_id', 'N/A')}")
                        st.write(f"**Patient ID:** {case_row.get('patient_id', 'N/A')}")
                        st.write(f"**Status:** {case_row.get('status', 'N/A')}")
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
                    
                    # Full case data as JSON (collapsible)
                    with st.expander("🔧 Raw Case Data"):
                        st.json(case_row)
                    
                    # Action buttons
                    st.markdown("**Actions:**")
                    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                    
                    with action_col1:
                        if st.button("✅ Mark Processed", key=f"process_{selected_case_id}", disabled=True):
                            pass
                            # if update_case_status(api_base_url, selected_case_id, "in Bearbeitung"):
                            #     st.cache_data.clear()  # Refresh data
                            #     st.rerun()
                    
                    with action_col2:
                        if st.button("🔄 Refresh Case", key=f"refresh_{selected_case_id}", disabled=True):
                            pass
                            # detailed_case = fetch_single_case(api_base_url, selected_case_id)
                            # if detailed_case:
                            #     st.success("✅ Case refreshed")
                            #     st.json(detailed_case)
                    
                    with action_col3:
                        if st.button("📋 View Lab Data", key=f"lab_{selected_case_id}", disabled=True):
                            pass 
                            # You can link to lab data product here
                            # lab_dp_url = "http://lab-dp-api:8001"
                            # st.info(f"🔗 Lab Data: {lab_dp_url}/api/v1/data-product/{case_row.get('product_id', 'unknown')}")
                    
                    with action_col4:
                        if st.button("🏁 Close Case", key=f"close_{selected_case_id}", disabled=True):
                            pass
                            # if update_case_status(api_base_url, selected_case_id, "abgeschlossen"):
                            #     st.cache_data.clear()  # Refresh data
                            #     st.rerun()
        
        else:
            st.warning("⚠️ No case_id column found in data")
    
    else:
        # Fallback: show all available columns
        st.dataframe(df_filtered, use_container_width=True, height=400)


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

# --- Footer ---
st.markdown("---")
st.markdown("Created with ❤️ by NASURE team 2025")