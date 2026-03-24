import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from data_processor import DataProcessor

# --- Configuration ---
st.set_page_config(
    page_title="Agile Intelligent Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styling & CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    /* Font for content only, avoid impacting UI elements like icons */
    .stApp, .stApp p, .stApp li, .stApp label, .stMarkdown, .stDataFrame, .kpi-label, .kpi-value, .header-tab-name {
        font-family: 'Inter', sans-serif !important;
    }

    /* Professional Header Styling */
    .brand-header {
        background: #ffffff;
        padding: 1.5rem 2rem;
        border-bottom: 2px solid #3b82f6;
        color: #1e293b;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .header-tab-name {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1c5998; /* Highlight Color: Professional Blue */
        display: flex;
        align-items: center;
        gap: 15px;
    }

    /* KPI Cards */
    .kpi-container {
        display: flex;
        gap: 20px;
        margin-bottom: 30px;
    }
    .kpi-card {
        background: #ffffff;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        flex: 1;
    }
    .kpi-label {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: #0f172a;
    }
    .kpi-value.ongoing { color: #d97706; } /* Professional Amber */
    .kpi-value.ontime { color: #059669; }  /* Professional Emerald */
    .kpi-value.delayed { color: #dc2626; } /* Professional Crimson */

    /* Footer */
    .dashboard-footer {
        padding: 2rem 0;
        color: #94a3b8;
        font-size: 0.85rem;
        text-align: center; /* Centered for balance */
        border-top: 1px solid #f1f5f9;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Components ---
def kpi_card(label, value, status_class=""):
    # Ensure value is formatted if it's a number
    if isinstance(value, (int, float)):
        # Format based on label
        if any(x in label.lower() for x in ["cost", "hour", "time spent"]):
            formatted_value = f"{value:,.1f}"
        else:
            formatted_value = f"{int(value):,}"
    else:
        formatted_value = value

    return f"""<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-value {status_class}'>{formatted_value}</div></div>"""

def brand_header(page_name):
    st.markdown(f"<div class='brand-header'><div class='header-tab-name'>{page_name}</div></div>", unsafe_allow_html=True)

def show_sidebar_logo(logo_image=None):
    if logo_image:
        st.sidebar.markdown(f"<div style='text-align:center; padding: 20px 0;'><img src='{logo_image}' style='width: 80%; border-radius: 8px;'></div>", unsafe_allow_html=True)
    else:
        # Simplified MobiFin Branding
        st.sidebar.markdown("<div style='text-align: center; background: white; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-top: 50px;'><div style='color: #1c5998; font-size: 24px; font-weight: 800; line-height: 1;'>MobiFin<span style='color: #f97316;'>.</span></div><div style='color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-top: 4px;'>A Bankai Company</div></div>", unsafe_allow_html=True)

def show_footer():
    st.markdown("<div class='dashboard-footer'>© 2026 Agile Intelligent Agent Dashboard. All Rights Reserved. &trade; MobiFin - A Bankai Company</div>", unsafe_allow_html=True)

def render_health_bar(done, inp, ns, label=None):
    # Determine the width of the label for proper spacing if needed, but here we just render distinct block.
    header_html = ""
    if label:
        header_html = f"<div style='font-family: Inter, sans-serif; font-weight: 700; font-size: 16px; color: #1e293b; margin-bottom: 8px;'>{label}</div>"
    
    bar_html = f"""
    <div style="font-family: 'Inter', sans-serif; margin-bottom: 20px;">
        {header_html}
        <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14px; font-weight: 600; color: #64748b;">{int(done)}% done</span>
            </div>
            <div style="display: flex; height: 16px; width: 100%; background-color: #f1f5f9; border-radius: 8px; overflow: hidden;">
                <div style="width: {done}%; background-color: #4e8e18;" title="Done: {done}%"></div>
                <div style="width: {inp}%; background-color: #2684ff;" title="In Progress: {inp}%"></div>
                <div style="width: {ns}%; background-color: #e2e8f0;" title="Not Started: {ns}%"></div>
            </div>
            <div style="display: flex; gap: 20px; margin-top: 12px; font-size: 13px; font-weight: 600;">
                <span style="color: #4e8e18;">Done <span style="color: #0f172a; font-size: 15px; margin-left: 4px;">{int(done)}%</span></span>
                <span style="color: #2684ff;">In progress <span style="color: #0f172a; font-size: 15px; margin-left: 4px;">{int(inp)}%</span></span>
                <span style="color: #64748b;">Not started <span style="color: #0f172a; font-size: 15px; margin-left: 4px;">{int(ns)}%</span></span>
            </div>
        </div>
    </div>
    """
    return bar_html

def render_epic_progress_bar(key, summary, pct, status, done_count, total_count):
    tooltip = f"Key: {key}&#10;Status: {status}&#10;Progress: {done_count}/{total_count} issues ({pct}%)"
    
    bar_html = f"""
    <div style="font-family: 'Inter', sans-serif; margin-bottom: 16px;" title="{tooltip}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px;">
                <span style="color: #2684ff; font-weight: 600; font-size: 14px;">{key}</span>
                <span style="color: #1e293b; font-size: 14px; margin-left: 8px;">{summary}</span>
            </div>
            <div style="font-size: 13px; font-weight: 600; color: #64748b; min-width: 60px; text-align: right;">{pct}% done</div>
        </div>
        <div style="height: 10px; width: 100%; background-color: #e2e8f0; border-radius: 5px; overflow: hidden;">
            <div style="width: {pct}%; height: 100%; background-color: #3b82f6;"></div>
        </div>
    </div>
    """
    return bar_html

def find_col_in_df(df, possible_names):
    if df is None or df.empty: return None
    return next((c for c in df.columns if c in possible_names), None)

# --- Styling Utilities ---
def style_dataframe(df):
    if df.empty: return df
    
    try:
        # Define formatting rules
        formats = {}
        for col in df.columns:
            if any(x in col.lower() for x in ["cost", "hour", "time spent", "velocity"]):
                formats[col] = "{:.1f}"
            elif pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_object_dtype(df[col]):
                formats[col] = "{:.0f}"
                
        # Basic formatting
        styler = df.style.format(formats, na_rep="N/A")

        # 1. Highlight Performance/Progress Columns
        target_cols = [c for c in df.columns if any(x in c.lower() for x in ["completed", "velocity", "total logged"])]
        if target_cols:
            styler = styler.background_gradient(subset=target_cols, cmap="Blues")

        # 2. Highlight Costs (Red tint for high cost)
        cost_cols = [c for c in df.columns if "cost" in c.lower()]
        if cost_cols:
            styler = styler.background_gradient(subset=cost_cols, cmap="Reds")

        # 3. Highlight Status Columns (On Time / Delayed)
        def highlight_status(val):
            if isinstance(val, str):
                val_l = val.lower()
                if 'delayed' in val_l:
                    return 'color: #dc2626; font-weight: 700;'
                elif 'on time' in val_l or 'compliant' in val_l:
                    return 'color: #059669; font-weight: 700;'
            return ''

        # Use applymap/map for element-wise styling (using applymap for older pandas compat)
        if hasattr(styler, 'map'):
            styler = styler.map(highlight_status)
        else:
            styler = styler.applymap(highlight_status)

        return styler
    except Exception as e:
        # Fallback to plain dataframe if styling fails
        print(f"DEBUG: Styling failed: {e}")
        return df

def safe_dataframe(df, **kwargs):
    """Safely renders a dataframe with styling, falling back to plain if it crashes."""
    if df is None or df.empty:
        st.info("No data available to display.")
        return

    try:
        # Try rendering WITH styling
        st.dataframe(style_dataframe(df), **kwargs)
    except Exception as e:
        # If that crashes (common with Large Datasets or Styler bugs), render PLAIN
        print(f"DEBUG: Render failed, falling back to plain: {e}")
        st.dataframe(df, **kwargs)

# @st.cache_data(ttl=3600) -> Removed to prevent caching IN_PROGRESS state. SQLite is fast enough.
def load_data():
    from agile_db_manager import AgileDatabaseManager
    
    # Try loading from DB first (Faster)
    db_path = "agile_database.db"
    
    # Check if DB exists and has data
    if os.path.exists(db_path):
        try:
            db = AgileDatabaseManager(db_path)
            data = db.get_all_tables()
            # Basic validation
            if data and not data.get("Issue Summary", pd.DataFrame()).empty:
                return data
        except Exception:
            pass # Fallback to Excel if DB fails
            
    # Fallback to Excel
    file_path = "Agile_Master_Data.xlsx"
    if not os.path.exists(file_path):
        return None
    
    fsize = os.path.getsize(file_path)
    if fsize < 1000:
        return "IN_PROGRESS"

    try:
        return pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
    except Exception as e:
        return "IN_PROGRESS"

def main():
    # --- Sidebar Configuration ---
    st.sidebar.markdown("### 🛠️ Configuration")
    if st.sidebar.button("🔄 Refresh Jira Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    data = load_data()
    
    if data == "IN_PROGRESS":
        st.warning("⏳ **Jira Data Extraction in Progress...**")
        st.info("The application is currently fetching fresh data from Jira. This page will refresh automatically as data becomes available.")
        st.markdown("""
            <div style="padding: 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                <p><b>What's happening?</b></p>
                <ul>
                    <li>Connecting to Jira Cloud...</li>
                    <li>Fetching Epic & Story hierarchies...</li>
                    <li>Calculating Sprint & Release metrics...</li>
                </ul>
                <p><i>Estimated time: 1-3 minutes depending on project size.</i></p>
            </div>
        """, unsafe_allow_html=True)
        # Auto refresh while waiting
        import time
        time.sleep(10)
        st.rerun()
        return

    if not data or not isinstance(data, dict):
        st.warning("Please extract data first.")
        st.info("Run `python agile_data_manager.py` to fetch data from Jira.")
        return

    # --- Data Enrichment (Fix for Year/Month Filters) ---
    for sheet in data:
        df = data[sheet]
        if df.empty: continue
        
        # Helper to find date column
        date_col = next((c for c in df.columns if any(x in c.lower() for x in ["date", "entry date", "creation date"])), None)
        
        if date_col:
            dt_series = pd.to_datetime(df[date_col], errors='coerce')
            if "Year" not in df.columns:
                df["Year"] = dt_series.dt.year.fillna(0).astype(int).astype(str).replace("0", "N/A")
            if "Month" not in df.columns:
                df["Month"] = dt_series.dt.strftime('%b').fillna("N/A")
        
        # Standardize for Worklog Summary specifically
        if sheet == "Worklog Summary":
            if "Worklog Year" not in df.columns: df["Worklog Year"] = df["Year"]
            if "Worklog Month" not in df.columns: df["Worklog Month"] = df["Month"]

    # --- Cross-Sheet Enrichment for Epics (REMOVED: Epics now have native Project data) ---
    # Legacy enrichment removed to prevent column duplication and overwriting.
    pass

    # --- Sidebar Configuration ---
    st.sidebar.markdown("### 🛠️ Configuration")

    if st.sidebar.button("🔄 Force Reload Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    
    # Navigation
    page_options = ["Sprint Summary", "Release Summary", "Epic Summary", "Agent Worklogs", "Non-compliance summary", "Issue Summary", "Defect Summary", "Finance Dashboard"]
    page = st.sidebar.selectbox("📍 Select Tab", page_options)
    st.sidebar.error(f"DEBUG PATH: {os.path.abspath(__file__)}")

    # Main Panel Filter UI
    brand_header(page)
    
    def get_unique(sheet, col_names):
        if sheet not in data: return []
        df_u = data[sheet]
        for col in col_names:
            if col in df_u.columns:
                vals = sorted([str(x) for x in df_u[col].dropna().unique() if str(x) != "N/A"])
                return vals
        return []

    with st.expander("🔍 Advanced Search & Filters", expanded=True):
        # Column setup
        f1, f2, f3, f4 = st.columns(4)
        
        # 1. Project (Common) - Standardize to Project Names ONLY
        # Build a mapping from all tables that have both Name and Key
        project_map = {}
        
        # Priority tables for mapping
        map_sources = ["Issue Summary", "Epic Summary", "Release Summary", "Worklog Summary"]
        for s in map_sources:
            if s in data:
                df_s = data[s]
                name_col = find_col_in_df(df_s, ["Project Name", "Project"])
                key_col = find_col_in_df(df_s, ["Project Key", "Key", "Project"])
                
                if name_col and key_col and name_col != key_col:
                    pairs = df_s[[name_col, key_col]].dropna().drop_duplicates()
                    for _, row in pairs.iterrows():
                        if row[name_col] and row[key_col]:
                            project_map[str(row[name_col])] = str(row[key_col]).split('-')[0] # Normalize key

        # Project Names for the dropdown
        # Cascading Logic: We want to find unique names.
        all_names = set()
        for s in ["Sprint Summary", "Epic Summary", "Issue Summary", "Release Summary", "Worklog Summary"]:
            if s in data:
                res = get_unique(s, ["Project Name"])
                if res: all_names.update(res)
        
        # Remove any keys that accidentally ended up in the name set
        final_names = sorted([n for n in all_names if n not in project_map.values()])
        
        projects = ["All Projects"] + final_names
        f_project = f1.selectbox("Project", projects)

        # Helper for Cascading Filters (Items available for selected project)
        def get_filtered_unique(sheet, col_names):
            if sheet not in data: return []
            df_scoped = data[sheet].copy()
            # Apply project filter ONLY (Using robust matching)
            if f_project != "All Projects":
                p_n = find_col_in_df(df_scoped, ["Project Name"])
                p_k = find_col_in_df(df_scoped, ["Project Key", "Project"])
                
                if p_n:
                    df_scoped = df_scoped[df_scoped[p_n].astype(str).str.strip() == str(f_project).strip()]
                elif p_k:
                    target_key = project_map.get(f_project)
                    match_key = str(target_key if target_key else f_project).strip()
                    df_scoped = df_scoped[df_scoped[p_k].astype(str).str.strip() == match_key]
            
            for col in col_names:
                if col in df_scoped.columns:
                    vals = [str(x).strip() for x in df_scoped[col].dropna().unique() if str(x).strip() not in ["N/A", ""]]
                    if vals:
                        return sorted(vals)
            return []
        
        # 2. Year & Month (Common)
        years = ["All"] + sorted(list(set(
            get_unique("Issue Summary", ["Year", "Created Date"]) + 
            get_unique("Worklog Summary", ["Year", "Worklog Year", "Time Entry Date"]) +
            get_unique("Sprint Summary", ["Year", "End Date"]) +
            get_unique("Release Summary", ["Year", "End Date"])
        )))
        f_year = f2.selectbox("Year", years)
        months = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        f_month = f3.selectbox("Month", months)

        # 4. Tab Specific Filters
        f_sprint, f_release, f_type, f_priority, f_status = "All", "All", "All", "All", "All"
        f_category, f_project_type, f_author = "All", "All", "All"

        if page == "Sprint Summary":
            sprints = ["All"] + get_filtered_unique("Sprint Summary", ["Sprint Name"])
            f_sprint = f4.selectbox("Sprint", sprints)
        
        elif page == "Release Summary" or page == "Defect Summary":
            releases = ["All"] + get_filtered_unique("Release Summary", ["Fix Version", "Release"])
            f_release = f4.selectbox("Release", releases)
        
        elif page == "Finance Dashboard":
            categories = ["All"] + get_unique("Worklog Summary", ["Project Category"])
            f_category = f4.selectbox("Project Category", categories)

        # Second row for more filters if needed
        if page in ["Issue Summary", "Defect Summary", "Finance Dashboard"]:
            st.markdown("---")
            f5, f6, f7, f8 = st.columns(4)
            if page == "Issue Summary":
                issue_types = ["All"] + get_unique("Issue Summary", ["Issue Type"])
                f_type = f5.selectbox("Issue Type", issue_types)
                priorities = ["All"] + get_unique("Issue Summary", ["Priority"])
                f_priority = f6.selectbox("Priority", priorities)
                statuses = ["All"] + get_unique("Issue Summary", ["Status", "Current Status"])
                f_status = f7.selectbox("Status", statuses)
            elif page == "Defect Summary":
                priorities = ["All"] + get_unique("Issue Summary", ["Priority"])
                f_priority = f5.selectbox("Priority", priorities)
                statuses = ["All"] + get_unique("Issue Summary", ["Status", "Current Status"])
                f_status = f6.selectbox("Status", statuses)
            elif page == "Finance Dashboard":
                project_types = ["All"] + get_unique("Worklog Summary", ["Project Type"])
                f_project_type = f5.selectbox("Project Type", project_types)
                authors = ["All"] + get_unique("Worklog Summary", ["Time Entry User"])
                f_author = f6.selectbox("Worklog Author", authors)
        
        # Hourly Rate Input (Conditioned to Release Summary or Finance Dashboard)
        hourly_rate = 50 # Default
        if page in ["Release Summary", "Finance Dashboard"]:
            st.markdown("---")
            c_rate, c_info = st.columns([1, 3])
            with c_rate:
                hourly_rate = st.number_input("Global Hourly Rate ($)", min_value=0, value=50, step=1, placeholder="Rate (e.g. 50)")
            with c_info:
                st.info("💡 This hourly rate is used for cost and invoicing analysis in Finance Dashboard.")

    processor = DataProcessor(hourly_rate=hourly_rate)

    # DEBUG: Show loaded table stats in Sidebar
    with st.sidebar.expander("📊 Data Debug", expanded=False):
        for k, v in data.items():
            if not v.empty:
                st.write(f"**{k}**: {len(v)} rows")
            else:
                st.write(f"**{k}**: Empty")

    # Filter helper
    def apply_filters(df):
        if df.empty: return df
        temp = df.copy()
        
        # Helper to find column
        def find_col(possible_names):
            return find_col_in_df(temp, possible_names)

        # 1. Project (Smart Filter: Handles Key vs Name mismatch)
        p_col_key = find_col(["Project Key", "Project"])
        p_col_name = find_col(["Project Name"])
        
        if f_project != "All Projects":
            if p_col_name:
                temp = temp[temp[p_col_name].astype(str).str.strip() == str(f_project).strip()]
            elif p_col_key:
                target_key = project_map.get(f_project)
                if target_key:
                    temp = temp[temp[p_col_key].astype(str).str.strip() == str(target_key).strip()]
                else:
                    temp = temp[temp[p_col_key].astype(str).str.strip() == str(f_project).strip()]
        
        # 2. Year
        y_col = find_col(["Year", "Worklog Year"])
        if f_year != "All" and y_col:
            temp = temp[temp[y_col].astype(str) == f_year]
            
        # 3. Month
        m_col = find_col(["Month", "Worklog Month"])
        if f_month != "All" and m_col:
            temp = temp[temp[m_col].astype(str).str.contains(f_month, case=False)]
            
        # 4. Sprint
        s_col = find_col(["Sprint Name", "Sprint"])
        if f_sprint != "All" and s_col:
            temp = temp[temp[s_col] == f_sprint]
            
        # 5. Release
        r_col = find_col(["Fix Version", "Release"])
        if f_release != "All" and r_col:
            temp = temp[temp[r_col] == f_release]
            
        # 6. Issue Type
        t_col = find_col(["Issue Type", "issuetype"])
        if f_type != "All" and t_col:
            temp = temp[temp[t_col] == f_type]
            
        # 7. Priority
        pr_col = find_col(["Priority", "priority"])
        if f_priority != "All" and pr_col:
            temp = temp[temp[pr_col] == f_priority]
            
        # 8. Status
        st_col = find_col(["Status", "Current Status", "State"])
        if f_status != "All" and st_col:
            temp = temp[temp[st_col] == f_status]

        # 9. Project Category
        cat_col = find_col(["Project Category", "projectCategory"])
        if f_category != "All" and cat_col:
            temp = temp[temp[cat_col] == f_category]

        # 10. Project Type
        pt_col = find_col(["Project Type", "projectType"])
        if f_project_type != "All" and pt_col:
            temp = temp[temp[pt_col] == f_project_type]

        # 11. Worklog Author
        a_col = find_col(["Time Entry User", "Worklog Author", "Author"])
        if f_author != "All" and a_col:
            temp = temp[temp[a_col] == f_author]

        return temp

    # --- Pages ---
    
    # 1. Sprint Summary (Image 0)
    if page == "Sprint Summary":
        df_raw = data.get("Sprint Summary", pd.DataFrame())
        # Pass Issue Summary for Health Calculation
        issue_df_filtered = apply_filters(data.get("Issue Summary", pd.DataFrame()))
        df, stats = processor.process_sprint_summary(apply_filters(df_raw), issue_df_filtered)
        
        if not df.empty:
            kpi_html = "<div class='kpi-container'>"
            kpi_html += kpi_card("Sprint Count", stats["Total Sprints"])
            kpi_html += kpi_card("Ongoing", stats["Ongoing"], "ongoing")
            kpi_html += kpi_card("On Time", stats["On Time"], "ontime")
            kpi_html += kpi_card("Delayed", stats["Delayed"], "delayed")
            kpi_html += kpi_card("Committed SP", stats["Committed SP"])
            kpi_html += kpi_card("Completed SP", stats["Completed SP"], "ontime")
            kpi_html += kpi_card("Done %", stats["Completion Rate"])
            kpi_html += "</div>"
            st.markdown(kpi_html, unsafe_allow_html=True)

            # Sprint Health Visual (Active/Selected)
            if "Health Done %" in df.columns:
                if f_sprint != "All":
                    # Specific Sprint Selected
                    row = df[df["Sprint Name"] == f_sprint]
                    if not row.empty:
                        d = row.iloc[0]['Health Done %']
                        i = row.iloc[0]['Health InProgress %']
                        n = row.iloc[0]['Health NotStarted %']
                        st.markdown(render_health_bar(d, i, n, f"📊 Health: {f_sprint}"), unsafe_allow_html=True)
                else:
                    # All Sprints - Show Active Only
                    # Use BROADER data context (ignore time filters, keep project filter)
                    # We need to re-process health for ALL active sprints in the project
                    full_sprint_df = data.get("Sprint Summary", pd.DataFrame())
                    full_issue_df = data.get("Issue Summary", pd.DataFrame())
                    
                    # Apply ONLY Project Filter
                    if f_project != "All Projects":
                        if "Project Name" in full_sprint_df.columns:
                            full_sprint_df = full_sprint_df[full_sprint_df["Project Name"] == f_project]
                        if "Project Name" in full_issue_df.columns:
                            full_issue_df = full_issue_df[full_issue_df["Project Name"] == f_project]
                            
                    # Get Active Sprints from this scope (Include Future as they might be started but not marked active)
                    active_broad_df = full_sprint_df[full_sprint_df['State'].str.lower().isin(['active', 'future'])]
                    
                    if not active_broad_df.empty:
                        # Process Health for these specific sprints
                        # We use the processor but need to be careful not to re-calculate stats for everything if slow.
                        # However, process_sprint_summary is fast enough for 2-3 sprints.
                        active_health_df, _ = processor.process_sprint_summary(active_broad_df, full_issue_df)
                        
                        st.markdown("#### ⚡ Active Sprint Health")
                        cols = st.columns(3) 
                        for idx, (idx_r, row) in enumerate(active_health_df.iterrows()):
                            with cols[idx % 3]:
                                st.markdown(render_health_bar(row['Health Done %'], row['Health InProgress %'], row['Health NotStarted %'], row['Sprint Name']), unsafe_allow_html=True)
                        st.markdown("---")

            # Epic Progress Visual
            if "Epic Summary" in data:
                 full_epic_df = data["Epic Summary"]
                 # Target: Issues in the filtered scope (Active/Selected Sprint) determines the relevant Epics
                 target_issue_df = issue_df_filtered 
                 
                 if not target_issue_df.empty and "Epic Link" in target_issue_df.columns:
                     related_epic_keys = target_issue_df["Epic Link"].dropna().unique()
                     # Filter Epic Summary
                     target_epics = full_epic_df[full_epic_df["Epic Key"].isin(related_epic_keys)]
                     
                     if not target_epics.empty:
                         st.markdown("#### 🚀 Epic Progress")
                         st.markdown(f"This sprint is working towards **{len(target_epics)} epics**")
                         
                         st.markdown("<div style='background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
                         
                         for _, epic_row in target_epics.iterrows():
                             total_issues = epic_row.get("Total Stories Count", 0)
                             completed_issues = epic_row.get("Completed Stories Count", 0)
                             summary = epic_row.get("Epic Summary", "")
                             key = epic_row.get("Epic Key", "")
                             status = epic_row.get("Epic Status", "")
                             
                             # Handle NaNs
                             total_issues = 0 if pd.isna(total_issues) else int(total_issues)
                             completed_issues = 0 if pd.isna(completed_issues) else int(completed_issues)
                             
                             pct = 0
                             if total_issues > 0:
                                 pct = int((completed_issues / total_issues) * 100)
                                 
                             st.markdown(render_epic_progress_bar(key, summary, pct, status, completed_issues, total_issues), unsafe_allow_html=True)
                         
                         st.markdown("</div>", unsafe_allow_html=True)
                         st.markdown("---")

            st.markdown("---")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown("#### 🏃 Sprint Details")
                cols = ["Sprint Name", "Start Date", "End Date", "Complete Date", "Count of Total Issues", "On Time / Delayed"]
                df_disp = df[[c for c in cols if c in df.columns]].rename(columns={
                    "Start Date": "Sprint Start Date", "End Date": "Sprint End Date", 
                    "Complete Date": "Sprint Complete Date", "Count of Total Issues": "Issue Count"
                })
                safe_dataframe(df_disp.sort_values("Sprint End Date", ascending=False), 
                             use_container_width=True, hide_index=True)
            with c2:
                st.markdown("#### 📋 Issues in Sprint")
                if "Issue Summary" in data:
                    iss_df = apply_filters(data["Issue Summary"])
                    type_breakdown = iss_df.groupby("Issue Type").size().reset_index(name="Issue Count").sort_values("Issue Count", ascending=False)
                    safe_dataframe(type_breakdown, use_container_width=True, hide_index=True)
        else:
            st.info("No Sprint data available.")

    # 2. Release Summary (Image 1)
    elif page == "Release Summary":
        try:
            # Apply filters to raw data first to ensure aggregation only counts filtered items
            filtered_data = {
                "Release Summary": apply_filters(data.get("Release Summary", pd.DataFrame())),
                "Sprint Summary": apply_filters(data.get("Sprint Summary", pd.DataFrame()))
            }
            df = processor.process_release_summary(filtered_data)
            
            if not df.empty:
                st.markdown("### 🚀 Release Summary Report")
                avg_vel = df["Velocity"].mean() if "Velocity" in df.columns else 0
                tot_cost = df["Overall Release Cost ($)"].sum() if "Overall Release Cost ($)" in df.columns else 0
                tot_sp = df["Story Points Completed"].sum() if "Story Points Completed" in df.columns else 0
                
                kpi_html = "<div class='kpi-container'>"
                kpi_html += kpi_card("Total Releases", len(df))
                kpi_html += kpi_card("Avg Velocity", f"{avg_vel:.1f}")
                kpi_html += kpi_card("Total Cost", f"${tot_cost:,.0f}")
                kpi_html += kpi_card("Total SP", int(tot_sp), "ontime")
                kpi_html += "</div>"
                st.markdown(kpi_html, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("#### 📋 Release KPI Table")
                df_display = df.rename(columns={"Fix Version": "Release", "Total work logged": "Total Logged Hours"})
                cols_to_show = ["Release", "Start Date", "End Date", "Feature Planned", "Feature completed",
                                "User Story Planned", "User Story Completed", 
                                "Total Logged Hours", "Head Count", "Users Logged > 8h", "Total Working Days", "Count of Sprints", 
                                "Count of Story Points", "Total Test Case Executed", "Velocity", "Total Defect", 
                                "Stability Ratio", "Time Spent / Story Point", 
                                "Time Spent / User", "Cost Per Story Point", "Overall Release Cost ($)"]
                
                safe_dataframe(df_display[[c for c in cols_to_show if c in df_display.columns]].sort_values("Release", ascending=False), 
                            use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("#### 📈 Release Performance Trends")
                c1, c2 = st.columns(2)
                with c1:
                    # Multi-color bars for Story Points
                    fig1 = px.bar(df, x="Fix Version", y="Story Points Completed", 
                                title="Story Point Completed per Release",
                                color="Fix Version", # Use color for visual distinction
                                text_auto='.0f',      # Add data labels
                                color_discrete_sequence=px.colors.qualitative.Prism)
                    st.plotly_chart(fig1, use_container_width=True)

                    fig2 = px.bar(df, x="Fix Version", y="Overall Release Cost ($)", 
                                title="Overall Release Cost ($)",
                                color="Fix Version",
                                text_auto='.0s', 
                                color_discrete_sequence=px.colors.qualitative.Safe)
                    st.plotly_chart(fig2, use_container_width=True)
                with c2:
                    fig3 = px.line(df, x="Fix Version", y="Velocity", 
                                title="Velocity per Release", 
                                markers=True,
                                text="Velocity", # Add labels to points
                                color_discrete_sequence=["#3b82f6"])
                    fig3.update_traces(textposition="top center")
                    st.plotly_chart(fig3, use_container_width=True)

                    fig4 = px.bar(df, x="Fix Version", y="Total work logged", 
                                title="Total Logged Hour per Release",
                                color="Fix Version",
                                text_auto='.1f',
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No Release data available.")
        except Exception as e:
            st.error(f"Error loading Release Summary: {e}")
            import traceback
            st.code(traceback.format_exc())

    # 3. Epic Summary
    elif page == "Epic Summary":
        try:
            epic_df = data.get("Epic Summary", pd.DataFrame())
            epic_df = apply_filters(epic_df)
            
            if not epic_df.empty:
                st.markdown("### 🏔️ Epic Summary Report")
                c_sp = epic_df["Completed Story Points"].sum() if "Completed Story Points" in epic_df.columns else 0
                r_sp = epic_df["Remaining Story Points"].sum() if "Remaining Story Points" in epic_df.columns else 0
                total_sp = c_sp + r_sp
                pct = (c_sp / total_sp * 100) if total_sp > 0 else 0
                
                kpi_html = "<div class='kpi-container'>"
                kpi_html += kpi_card("Total Epics", len(epic_df))
                kpi_html += kpi_card("Completed SP", int(c_sp), "ontime")
                kpi_html += kpi_card("Remaining SP", int(r_sp))
                kpi_html += kpi_card("% Completion", f"{pct:.1f}%")
                kpi_html += "</div>"
                st.markdown(kpi_html, unsafe_allow_html=True)
                
                st.markdown("---")
                safe_dataframe(epic_df, use_container_width=True, hide_index=True)
            else:
                st.info("No Epic data available.")
        except Exception as e:
            st.error(f"Error loading Epic Summary: {e}")

    # 4. Agent Worklogs
    elif page == "Agent Worklogs":
        try:
            wl_df = data.get("Worklog Summary", pd.DataFrame())
            if not wl_df.empty:
                # Use apply_filters directly (it handles Project Key via map if needed)
                wl_df = apply_filters(wl_df)
                
                pivot_df, sorted_months = processor.process_worklog_summary(wl_df)
                
                if not pivot_df.empty:
                    st.markdown("### 👥 Agent Worklog Summary")
                    kpi_html = "<div class='kpi-container'>"
                    kpi_html += kpi_card("Total Hours Logged", int(wl_df["Sum of Time Entry Log Time"].sum()))
                    kpi_html += kpi_card("Active Team Members", len(pivot_df))
                    kpi_html += "</div>"
                    st.markdown(kpi_html, unsafe_allow_html=True)


                    
                    st.markdown("---")
                    st.markdown("#### 📅 Monthly Worklog Pivot (Hours)")
                    # Sort columns: User, then months, then Total
                    cols_order = ["Time Entry User"] + sorted_months + ["Total Hours"]
                    # Ensure columns exist in pivot_df
                    valid_cols = [c for c in cols_order if c in pivot_df.columns]
                    safe_dataframe(pivot_df[valid_cols], use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.markdown("#### 📊 Productivity Trends")
                    c1, c2 = st.columns(2)
                    with c1:
                        # Top 10 Loggers
                        top_loggers = pivot_df.sort_values("Total Hours", ascending=True).tail(10)
                        st.plotly_chart(px.bar(top_loggers, x="Total Hours", y="Time Entry User", 
                                               orientation='h', title="Top 10 Loggers (Total Hours)",
                                               color_discrete_sequence=["#10b981"]), use_container_width=True)
                    with c2:
                        # Hours per Month Trend
                        monthly_totals = wl_df.copy()
                        monthly_totals['Month'] = pd.to_datetime(monthly_totals['Time Entry Date']).dt.to_period('M').dt.to_timestamp()
                        m_trend = monthly_totals.groupby('Month')['Sum of Time Entry Log Time'].sum().reset_index()
                        st.plotly_chart(px.line(m_trend, x="Month", y="Sum of Time Entry Log Time", 
                                                title="Total Hours Logged per Month", markers=True,
                                                color_discrete_sequence=["#3b82f6"]), use_container_width=True)

                    st.markdown("---")
                    st.markdown("#### ⚠️ Late Logs on Completed Issues (>15d Backdated)")
                    backdated_report = processor.process_backdated_worklogs(data)
                    if not backdated_report.empty:
                        st.warning(f"Found {len(backdated_report)} worklogs added after issue resolution with >15 day backdate.")
                        safe_dataframe(backdated_report, use_container_width=True, hide_index=True)
                    else:
                        st.success("No late backdated logs found on completed issues. Great job!")
                else:
                    st.info("No worklog details found for the current filter.")
            else:
                st.info("No Worklog metadata available. Please run data extraction first.")
        except Exception as e:
            st.error(f"Error loading Agent Worklogs: {e}")

    # 5. Issue Summary (Image 2)
    elif page == "Issue Summary":
        issue_df = apply_filters(data.get("Issue Summary", pd.DataFrame()))
        stats = processor.process_issue_summary(issue_df)
        
        if stats:
            kpi_html = "<div class='kpi-container'>"
            kpi_html += kpi_card("Total Issues", stats['Total Issues'])
            kpi_html += kpi_card("Unique Projects", len(stats["By Project"]))
            kpi_html += "</div>"
            st.markdown(kpi_html, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                # User Pie
                fig1 = px.pie(names=list(stats["By User"].keys()), values=list(stats["By User"].values()), hole=0.5, title="Issue Count By User")
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                fig1.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
                st.plotly_chart(fig1, use_container_width=True)

                # Type Bar
                st.plotly_chart(px.bar(x=list(stats["By Type"].keys()), y=list(stats["By Type"].values()), title="Issue Count By Issue Type"), use_container_width=True)
                
                # Month Bar
                st.plotly_chart(px.bar(x=list(stats["By Month"].keys()), y=list(stats["By Month"].values()), title="Issue Count By Month"), use_container_width=True)

            with c2:
                # Priority Pie
                fig2 = px.pie(names=list(stats["By Priority"].keys()), values=list(stats["By Priority"].values()), title="Issue Count Priority")
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)
                
                # Project Type Pie
                fig3 = px.pie(names=list(stats["By Project"].keys()), values=list(stats["By Project"].values()), title="Issue Count By Project Type")
                fig3.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig3, use_container_width=True)
                
                # Status Pie
                fig4 = px.pie(names=list(stats["By Status"].keys()), values=list(stats["By Status"].values()), title="Issue Count By Issue Status")
                fig4.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig4, use_container_width=True)

    # 4. Defect Summary
    elif page == "Defect Summary":
        defects = processor.process_defect_summary(data)
        defects = apply_filters(defects)
        
        if not defects.empty:
            kpi_html = "<div class='kpi-container'>"
            kpi_html += kpi_card("Total Defects", len(defects), "delayed")
            kpi_html += "</div>"
            st.markdown(kpi_html, unsafe_allow_html=True)
            
            st.markdown("### 🐞 Defect Summary Report")
            c1, c2, c3 = st.columns(3)
            with c1:
                rel_df = defects.groupby("Fix Version").size().reset_index(name="Count")
                st.plotly_chart(px.bar(rel_df, x="Fix Version", y="Count", title="Defects by Release"), use_container_width=True)
            with c2:
                pri_df = defects.groupby("Priority").size().reset_index(name="Count")
                st.plotly_chart(px.pie(pri_df, names="Priority", values="Count", hole=0.4, title="Defects by Priority"), use_container_width=True)
            with c3:
                defects['Status Group'] = defects['Current Status'].apply(lambda x: 'Closed' if str(x).lower() in ['done', 'closed', 'resolved', 'released'] else 'Open')
                stat_df = defects.groupby("Status Group").size().reset_index(name="Count")
                st.plotly_chart(px.pie(stat_df, names="Status Group", values="Count", color_discrete_map={'Open': '#ef4444', 'Closed': '#10b981'}, title="Status: Open vs Close"), use_container_width=True)

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                time_rel = defects.groupby("Fix Version")["Sum of Time Entry Log Time"].sum().reset_index()
                st.plotly_chart(px.bar(time_rel, x="Fix Version", y="Sum of Time Entry Log Time", title="Time Spent on Defect by Release"), use_container_width=True)
            with c2:
                time_auth = defects.groupby("Assignee Name")["Sum of Time Entry Log Time"].sum().sort_values(ascending=False).reset_index()
                st.plotly_chart(px.bar(time_auth.head(10), x="Assignee Name", y="Sum of Time Entry Log Time", title="Time Spent by Contributor"), use_container_width=True)

            st.markdown("---")
            st.markdown("---")
            st.markdown("#### 🧩 Defect Breakdown")

            t1, t2 = st.tabs(["📊 By Sprint & Release", "📖 By Story"])
            
            with t1:
                c_sprint, c_release = st.columns(2)
                
                with c_sprint:
                    st.markdown("##### Defects by Sprint")
                    if 'Sprint Name' in defects.columns: 
                        s_col = 'Sprint Name' 
                    elif 'Sprint' in defects.columns:
                        s_col = 'Sprint'
                    else:
                        s_col = None

                    if s_col:
                        # 1. Defect Counts
                        sprint_defect_counts = defects.groupby(s_col).size().reset_index(name='Defect Count')
                        
                        # 2. Story Counts (Context)
                        # Ensure we use FILTERED issue data for story context
                        raw_issue_df = apply_filters(data.get("Issue Summary", pd.DataFrame()))
                        if not raw_issue_df.empty and 'Issue Type' in raw_issue_df.columns:
                            # CRITICAL FIX: Raw data might only have Sprint ID. Enrich with Sprint Name.
                            if 'Sprint Name' not in raw_issue_df.columns and 'Sprint ID' in raw_issue_df.columns:
                                sprint_summ = data.get("Sprint Summary", pd.DataFrame())
                                if not sprint_summ.empty:
                                    sprint_map = sprint_summ.set_index('Sprint ID')['Sprint Name'].to_dict()
                                    raw_issue_df['Sprint Name'] = raw_issue_df['Sprint ID'].map(sprint_map)
                            
                            # Filter for Stories
                            stories = raw_issue_df[raw_issue_df['Issue Type'].astype(str).str.lower() == 'story']
                            # We need to ensure we use the same Sprint Column name if possible. 
                            # Issue Summary usually has 'Sprint Name' or 'Sprint'
                            raw_s_col = 'Sprint Name' if 'Sprint Name' in raw_issue_df.columns else 'Sprint'
                            
                            if raw_s_col in stories.columns:
                                sprint_story_counts = stories.groupby(raw_s_col).size().reset_index(name='Story Count')
                                # Merge
                                merged_counts = pd.merge(sprint_defect_counts, sprint_story_counts, left_on=s_col, right_on=raw_s_col, how='outer').fillna(0)
                                if s_col != raw_s_col:
                                    merged_counts[s_col] = merged_counts[s_col].fillna(merged_counts[raw_s_col])
                                    merged_counts.drop(columns=[raw_s_col], inplace=True)
                                
                                # Format
                                merged_counts['Story Count'] = merged_counts['Story Count'].astype(int)
                                merged_counts['Defect Count'] = merged_counts['Defect Count'].astype(int)
                                
                                # Sort by Defect Count
                                merged_counts = merged_counts.sort_values('Defect Count', ascending=False)
                                safe_dataframe(merged_counts, use_container_width=True, hide_index=True)
                            else:
                                safe_dataframe(sprint_defect_counts.sort_values('Defect Count', ascending=False), use_container_width=True, hide_index=True)
                        else:
                            safe_dataframe(sprint_defect_counts.sort_values('Defect Count', ascending=False), use_container_width=True, hide_index=True)

                    else:
                        st.info("Sprint info unavailable")

                with c_release:
                    st.markdown("##### Defects by Release")
                    rel_counts = defects.groupby("Fix Version").size().reset_index(name='Defect Count').sort_values('Defect Count', ascending=False)
                    safe_dataframe(rel_counts, use_container_width=True, hide_index=True)

            with t2:
                st.markdown("##### Defects by Story")
                if 'Parent Issue Key' in defects.columns:
                    # Try to include Summary if available
                    grp_cols = ['Parent Issue Key']
                    if 'Parent Issue Summary' in defects.columns:
                        grp_cols.append('Parent Issue Summary')
                    
                    story_counts = defects.groupby(grp_cols).size().reset_index(name='Defect Count').sort_values('Defect Count', ascending=False)
                    safe_dataframe(story_counts, use_container_width=True, hide_index=True)
                else:
                    st.info("Parent Story info unavailable")
        else:
            st.info("No Defects found.")


    # 6. Non-compliance Summary
    elif page == "Non-compliance summary":
        sprint_df = apply_filters(data.get("Sprint Summary", pd.DataFrame()))
        if not sprint_df.empty:
            # Filter for Active and Future Sprints only
            af_sprints = sprint_df[sprint_df['State'].str.lower().isin(['active', 'future'])]
            if not af_sprints.empty:
                sprint_list = af_sprints['Sprint Name'].tolist()
                sel_sprint_name = st.selectbox("Select Sprint to check compliance", sprint_list)
                sel_sprint_id = af_sprints[af_sprints['Sprint Name'] == sel_sprint_name]['Sprint ID'].iloc[0]
                
                # Brand Header for the section
                st.markdown(f"### 📋 Sprint Compliance Report: {sel_sprint_name}")
                st.write(f"DEBUG: Selected Sprint Name: {sel_sprint_name}, ID: {sel_sprint_id}")
                st.write(f"DEBUG: Current Page state: {page}")
                
                try:
                    compliance_rules = processor.process_non_compliance(data, sprint_id=sel_sprint_id)
                    st.write(f"DEBUG: Rules generated: {len(compliance_rules) if compliance_rules else 0}")
                except Exception as e:
                    import traceback
                    st.error(f"CRASH in process_non_compliance: {str(e)}")
                    st.code(traceback.format_exc())
                    compliance_rules = []
                
                if compliance_rules:
                    # Render custom HTML table for premium look
                    table_html = "" 
                    try:
                        table_html = "<table style='width:100%; border-collapse: collapse; margin-top: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);'>"
                        table_html += "<thead><tr style='background-color: #f8fafc; border-bottom: 2px solid #e2e8f0;'>"
                        table_html += "<th style='padding: 15px; text-align: left; font-weight: 600; color: #475569;'>Compliance CheckPoint</th>"
                        table_html += "<th style='padding: 15px; text-align: center; font-weight: 600; color: #475569;'>Compliance Score</th>"
                        table_html += "<th style='padding: 15px; text-align: left; font-weight: 600; color: #475569;'>Issue keys</th>"
                        table_html += "</tr></thead><tbody>"
                        
                        import html
                        for row in compliance_rules:
                            score = str(row.get("Compliance Score", "N/A"))
                            color = "#10b981" if score == "Green" else "#ef4444"
                            icon = "🟢" if score == "Green" else "🔴"
                            score_html = f"<div style='display:flex; justify-content:center; align-items:center;'><span title='{score}' style='color:{color}; font-size:18px;'>{icon}</span></div>"
                            
                            keys_raw = row.get("Issue keys", "-")
                            keys_escaped = html.escape(str(keys_raw))
                            checkpoint = html.escape(str(row.get("Compliance CheckPoint", "Unknown")))
                            
                            table_html += f"<tr style='background-color: white; border-bottom: 1px solid #f1f5f9;'>"
                            table_html += f"<td style='padding: 12px 15px; color: #1e293b; font-weight: 500; border-left: 4px solid {color};'>{checkpoint}</td>"
                            table_html += f"<td style='padding: 12px 15px; text-align: center;'>{score_html}</td>"
                            table_html += f"<td style='padding: 12px 15px; color: #64748b; font-size: 13px; font-family: monospace; max-width: 400px; word-wrap: break-word;'>{keys_escaped}</td>"
                            table_html += "</tr>"
                        table_html += "</tbody></table>"
                        st.markdown(table_html, unsafe_allow_html=True)
                    except Exception as html_err:
                        st.warning(f"Note: Premium table rendering failed, showing standard view. ({str(html_err)})")
                        df_comp = pd.DataFrame(compliance_rules)
                        safe_dataframe(df_comp, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.caption("💡 **Green (🟢)** indicates 100% compliance. **Red (🔴)** indicates issues requiring attention.")
                    
                    st.markdown("---")
                    st.markdown("### 🌍 Global Non-Compliance Audit (All Sprints & Backlog)")
                    st.info("This table audits ALL extracted issues, including completed, in-progress, and backlog items across all historical sprints.")
                    
                    try:
                        global_rules = processor.process_non_compliance(data, global_audit=True)
                        if global_rules:
                            global_df = pd.DataFrame(global_rules)
                            safe_dataframe(global_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("No global non-compliance issues found. Excellent project hygiene!")
                    except Exception as g_err:
                        st.error(f"Global Audit Error: {g_err}")

                else:
                    st.success("🎉 All checked sprins/issues are 100% compliant!")
            else:
                st.info("No Active or Future sprints found to audit. This tab focuses on planning hygiene.")
        else:
            st.warning("Sprint metadata not found. Please refresh data extraction.")

    # 7. Finance Dashboard (Image 0 & 1)
    elif page == "Finance Dashboard":
        wl_df = data.get("Worklog Summary", pd.DataFrame())
        if not wl_df.empty:
            # Apply common filters
            df = apply_filters(wl_df)
            
            # Process for metrics
            df_processed, stats = processor.process_finance_summary(df)
            
            if not df_processed.empty:
                # KPIs (Image 1 Style)
                st.markdown("### 💰 Financial & Invoicing Analysis")
                k_col1, k_col2, k_col3, k_col4 = st.columns(4)
                
                with k_col1:
                    st.markdown(kpi_card("Total Time - Hours", stats["Total Hours"]), unsafe_allow_html=True)
                with k_col2:
                    st.markdown(kpi_card("Total Issue Count", stats["Total Issues"]), unsafe_allow_html=True)
                with k_col3:
                    st.markdown(kpi_card("Work Log Users", stats["Total Users"]), unsafe_allow_html=True)
                with k_col4:
                    total_cost = stats["Total Hours"] * hourly_rate
                    st.markdown(kpi_card("Invoicing Amount", f"${total_cost:,.0f}"), unsafe_allow_html=True)

                st.markdown("---")
                
                # Pivot Table (Image 0 Style)
                st.markdown("#### 📅 User Details - Time Entry (Month-wise)")
                pivot_df, sorted_months = processor.process_worklog_summary(df)
                if not pivot_df.empty:
                    # Rename columns to match image (May, June, etc.)
                    # Note: processed months are like Jan-23, Apr-24, etc.
                    # For the premium look, we'll use the pivot as is.
                    safe_dataframe(pivot_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # Bottom Charts (Image 1 Style)
                c1, c2 = st.columns(2)
                
                with c1:
                    # Month wise Hours
                    m_data = df.groupby('Month')['Sum of Time Entry Log Time'].sum().reset_index()
                    fig_m = px.bar(m_data, x='Month', y='Sum of Time Entry Log Time', 
                                 title="Month wise Hours", 
                                 text_auto='.0f',
                                 color_discrete_sequence=['#3b82f6'])
                    st.plotly_chart(fig_m, use_container_width=True)

                    # Product Map (Project Category Distribution)
                    cat_data = df.groupby('Project Category')['Sum of Time Entry Log Time'].sum().reset_index()
                    fig_cat = px.pie(cat_data, names='Project Category', values='Sum of Time Entry Log Time', 
                                    hole=0.5, title="Product Map - Hours (By Category)")
                    st.plotly_chart(fig_cat, use_container_width=True)

                with c2:
                    # Delivery - Hours (By Project Name)
                    p_data = df.groupby('Project Name')['Sum of Time Entry Log Time'].sum().reset_index().sort_values('Sum of Time Entry Log Time', ascending=False).head(15)
                    fig_p = px.pie(p_data, names='Project Name', values='Sum of Time Entry Log Time', 
                                 hole=0.5, title="Delivery - Hours (Top 15 Projects)")
                    st.plotly_chart(fig_p, use_container_width=True)
                    
                    # Issue Type breakdown
                    type_data = df.groupby('Issue Type')['Sum of Time Entry Log Time'].sum().reset_index()
                    fig_type = px.bar(type_data, x='Sum of Time Entry Log Time', y='Issue Type', 
                                    orientation='h', title="Hours by Issue Type",
                                    color_discrete_sequence=['#10b981'])
                    st.plotly_chart(fig_type, use_container_width=True)
                
                # Financial Breakdown Table & Export
                st.markdown("---")
                st.markdown("#### 📑 Category-wise Financial Breakdown")
                finance_table = df.groupby('Project Category').agg({
                    'Sum of Time Entry Log Time': 'sum',
                    'Key': 'nunique',
                    'Time Entry User': 'nunique'
                }).reset_index().rename(columns={
                    'Sum of Time Entry Log Time': 'Total Hours',
                    'Key': 'Issues Count',
                    'Time Entry User': 'Head Count'
                })
                finance_table['Estimated Cost'] = finance_table['Total Hours'] * hourly_rate
                safe_dataframe(finance_table, use_container_width=True, hide_index=True)

                if finance_table.shape[0] <= 1:
                    st.markdown("#### 🏗️ Project-wise Financial Breakdown")
                    proj_finance_table = df.groupby('Project Name').agg({
                        'Sum of Time Entry Log Time': 'sum',
                        'Key': 'nunique',
                        'Time Entry User': 'nunique'
                    }).reset_index().rename(columns={
                        'Sum of Time Entry Log Time': 'Total Hours',
                        'Key': 'Issues Count',
                        'Time Entry User': 'Head Count'
                    })
                    proj_finance_table['Estimated Cost'] = proj_finance_table['Total Hours'] * hourly_rate
                    safe_dataframe(proj_finance_table, use_container_width=True, hide_index=True)
                
                # Export Button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Finance Data (CSV)",
                    data=csv,
                    file_name=f"finance_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No worklog data found for the current filters.")
        else:
            st.warning("Worklog Summary sheet not found. Please verify your data extraction.")

    # Footer
    show_footer()

if __name__ == "__main__":
    main()
