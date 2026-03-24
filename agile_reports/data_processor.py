import pandas as pd
import numpy as np
from datetime import datetime

class DataProcessor:
    def __init__(self, hourly_rate=50):
        self.hourly_rate = hourly_rate

    def process_sprint_summary(self, sprint_df, issue_df=None):
        """Enhances sprint data with On-Time/Delayed status and Sprint Health."""
        if sprint_df.empty:
            return pd.DataFrame(), {}

        df = sprint_df.copy()
        
        # Helper to handle date parsing
        def parse_jira_date(d):
            if pd.isna(d) or d == 'NaN' or d == '': return None
            try:
                dt = pd.to_datetime(d)
                if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                    return dt.tz_convert(None)
                return dt
            except:
                return None
        

        # Convert date columns
        date_cols = ['Start Date', 'End Date', 'Complete Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)

        # Calculate On Time / Delayed
        def get_status(row):
            now = pd.Timestamp.now().replace(tzinfo=None) # Explicitly naive
            comp_date = row.get('Complete Date')
            end_date = row.get('End Date')
            
            if pd.isna(comp_date):
                if pd.isna(end_date): return "Unknown"
                return "On Time" if now <= end_date.replace(tzinfo=None) else "Delayed"
            return "On Time" if comp_date.replace(tzinfo=None) <= end_date.replace(tzinfo=None) else "Delayed"

        df['On Time / Delayed'] = df.apply(get_status, axis=1)

        # Calculate Sprint Health (Done/In Progress/Not Started)
        def get_health(row, issue_df_loc):
            if issue_df_loc is None or issue_df_loc.empty:
                return 0, 0, 0, 0
            
            sid = row.get('Sprint ID')
            if not sid: return 0, 0, 0, 0
            
            s_issues = issue_df_loc[issue_df_loc['Sprint ID'] == sid].copy()
            if s_issues.empty: return 0, 0, 0, 0
            
            # Categories based on user confirmation
            st_done = ['done', 'closed', 'released', 'resolved', 'fixed', 'work done', 'devops done', 'execution done', 'dev. done']
            st_inp = ['in progress', 'in development', 'dev. in progress', 'in review', 'in qa', 'in analysis', 're-test', 'execution in progress', 'ready for release', 'in design']
            # Everything else is Not Started
            
            def map_status(s):
                s = str(s).lower().strip()
                if s in st_done: return 'Done'
                if s in st_inp: return 'InProgress'
                return 'NotStarted'
            
            s_issues['HealthCat'] = s_issues['Current Status'].apply(map_status)
            
            # Find SP column
            sp_col = next((c for c in s_issues.columns if any(x in c.lower() for x in ["story points", "story point", "completed sp"])), None)
            
            d_pct, i_pct, n_pct, completeness = 0, 0, 0, 0

            # Calculate Health
            if sp_col:
                total_sp = s_issues[sp_col].sum()
                if total_sp > 0:
                    d = s_issues[s_issues['HealthCat']=='Done'][sp_col].sum()
                    i = s_issues[s_issues['HealthCat']=='InProgress'][sp_col].sum()
                    n = s_issues[s_issues['HealthCat']=='NotStarted'][sp_col].sum()
                    d_pct, i_pct, n_pct = d/total_sp*100, i/total_sp*100, n/total_sp*100
                    # For total progress bar (Done), use d_pct.
                    completeness = int(d_pct)
            
            if d_pct == 0 and i_pct == 0 and n_pct == 0:
                # Fallback to Count
                total = len(s_issues)
                if total > 0:
                    d = len(s_issues[s_issues['HealthCat']=='Done'])
                    i = len(s_issues[s_issues['HealthCat']=='InProgress'])
                    n = len(s_issues[s_issues['HealthCat']=='NotStarted'])
                    d_pct, i_pct, n_pct = d/total*100, i/total*100, n/total*100
                    completeness = int(d_pct)

            return round(d_pct), round(i_pct), round(n_pct), completeness

        if issue_df is not None:
            # Apply to each row
            health_metrics = df.apply(lambda r: get_health(r, issue_df), axis=1)
            df['Health Done %'] = [x[0] for x in health_metrics]
            df['Health InProgress %'] = [x[1] for x in health_metrics]
            df['Health NotStarted %'] = [x[2] for x in health_metrics]
            df['Sprint Progress %'] = [x[3] for x in health_metrics]
        else:
             df['Health Done %'] = 0
             df['Health InProgress %'] = 0
             df['Health NotStarted %'] = 0
             df['Sprint Progress %'] = 0

        # Aggregates
        stats = {
            "Total Sprints": len(df),
            "Ongoing": len(df[df['State'].str.lower() == 'active']) if 'State' in df.columns else 0,
            "On Time": len(df[df['On Time / Delayed'] == 'On Time']),
            "Delayed": len(df[df['On Time / Delayed'] == 'Delayed']),
            "Committed SP": int(df["Total of Committed Story Points"].sum()) if "Total of Committed Story Points" in df.columns else 0,
            "Completed SP": int(df["Total of Completed Story Points"].sum()) if "Total of Completed Story Points" in df.columns else 0
        }
        
        rates = stats["Completed SP"] / stats["Committed SP"] if stats["Committed SP"] > 0 else 0
        stats["Completion Rate"] = f"{rates*100:.1f}%"

        return df, stats

    def calculate_velocity(self, sprint_df):
        """Calculates historical velocity from Sprint Summary."""
        if sprint_df.empty or "Total of Completed Story Points" not in sprint_df.columns:
            return 0.0
        
        closed_sprints = sprint_df[sprint_df['State'].str.lower() == 'closed'] if 'State' in sprint_df.columns else sprint_df
        if closed_sprints.empty:
            return 0.0
        
        return round(closed_sprints["Total of Completed Story Points"].mean(), 2)

    def process_release_summary(self, data_dict):
        """Comprehensive release metrics as per UI Image 1."""
        raw_df = data_dict.get("Release Summary", pd.DataFrame()).copy()
        sprint_df = data_dict.get("Sprint Summary", pd.DataFrame())
        
        if raw_df.empty:
            return pd.DataFrame()

        # Aggregation Logic to handle multi-project duplicates
        agg_map = {
            "Start Date": "min",
            "End Date": "max",
            "Feature Planned": "sum",
            "Feature completed": "sum",
            "User Story Planned": "sum",
            "User Story Completed": "sum",
            "Story Points Committed": "sum",
            "Story Points Completed": "sum",
            "Story Points Remaining": "sum",
            "Total Issues": "sum",
            "Total Completed Issues": "sum",
            "Total Defect": "sum",
            "Total Test Case Executed": "sum",
            "Head Count": "sum",
            "Total work logged": "sum",
            "Users Logged > 8h": lambda x: ", ".join(sorted(list(set([u.strip() for val in x if pd.notna(val) for u in str(val).split(",") if u.strip()])))),
            "Full Worklog Breakdown": lambda x: "\n".join([str(val) for val in x if pd.notna(val)])
        }
        
        # Ensure dates are datetime for min/max
        raw_df["Start Date"] = pd.to_datetime(raw_df["Start Date"], errors='coerce')
        raw_df["End Date"] = pd.to_datetime(raw_df["End Date"], errors='coerce')
        
        # Filter agg_map to existing columns
        agg_map = {k: v for k, v in agg_map.items() if k in raw_df.columns}
        
        release_df = raw_df.groupby("Fix Version").agg(agg_map).reset_index()

        # Helper for working days
        def get_working_days(start, end):
            if pd.isna(start) or pd.isna(end): return 0
            try:
                # Force to date only (remove time/timezone)
                s = pd.to_datetime(start).tz_localize(None).normalize()
                e = pd.to_datetime(end).tz_localize(None).normalize()
                if s > e: return 0
                # bdate_range is inclusive of both endpoints
                return len(pd.bdate_range(s, e))
            except Exception:
                return 0

        release_df["Total Working Days"] = release_df.apply(lambda x: get_working_days(x["Start Date"], x["End Date"]), axis=1)

        # Count of Sprints
        def get_sprint_count(version):
            if sprint_df.empty: return 0
            return len(sprint_df[sprint_df['Fix Versions'].astype(str).str.contains(str(version), na=False)])

        release_df["Count of Sprints"] = release_df["Fix Version"].apply(get_sprint_count)
        release_df["Count of Story Points"] = release_df["Story Points Completed"]

        # Financials
        release_df["Overall Release Cost ($)"] = release_df["Total work logged"] * self.hourly_rate
        
        # Time Spent / Story Point
        release_df["Time Spent / Story Point"] = release_df.apply(
            lambda x: x["Total work logged"] / x["Story Points Completed"] if x["Story Points Completed"] > 0 else 0,
            axis=1
        ).round(2)

        # Time Spent / User
        release_df["Time Spent / User"] = release_df.apply(
            lambda x: x["Total work logged"] / x["Head Count"] if x["Head Count"] > 0 else 0,
            axis=1
        ).round(2)

        # Cost Per Story Point
        release_df["Cost Per Story Point"] = release_df.apply(
            lambda x: x["Overall Release Cost ($)"] / x["Story Points Completed"] if x["Story Points Completed"] > 0 else 0,
            axis=1
        ).round(2)

        # Stability Ratio
        release_df["Stability Ratio"] = release_df.apply(
            lambda x: 1 - (x["Total Defect"] / x["Total Test Case Executed"]) if x["Total Test Case Executed"] > 0 else 1.0,
            axis=1
        ).round(2)

        # Velocity per Release
        def get_release_velocity(version):
            if sprint_df.empty: return 0
            mask = sprint_df['Fix Versions'].astype(str).str.contains(str(version), na=False)
            relevant_sprints = sprint_df[mask]
            if relevant_sprints.empty: return 0
            return relevant_sprints['Total of Completed Story Points'].mean()

        release_df['Velocity'] = release_df['Fix Version'].apply(get_release_velocity).round(2)
        
        return release_df

    def process_finance_summary(self, worklog_df):
        """Processes worklogs for financial reporting as per Image 0 & 1."""
        if worklog_df.empty:
            return pd.DataFrame(), {}

        df = worklog_df.copy()
        # Parse dates
        df['Time Entry Date'] = pd.to_datetime(df['Time Entry Date'], errors='coerce')
        df['Month'] = df['Time Entry Date'].dt.strftime('%B')
        df['Year'] = df['Time Entry Date'].dt.year
        df['Project Name'] = df['Project Name'].fillna('Unknown')

        # Stats
        stats = {
            "Total Hours": df['Sum of Time Entry Log Time'].sum(),
            "Total Issues": df['Key'].nunique(),
            "Total Users": df['Time Entry User'].nunique()
        }

        return df, stats

    def process_issue_summary(self, issue_df):
        """Aggregates for Issue Summary tab (Image 2)."""
        if issue_df.empty:
            return {}

        # Ensure Created Date is datetime
        issue_df['Created Date'] = pd.to_datetime(issue_df['Created Date'], errors='coerce')
        issue_df['Month'] = issue_df['Created Date'].dt.strftime('%B')
        
        return {
            "Total Issues": len(issue_df),
            "By User": issue_df.groupby("Assignee Name").size().to_dict(),
            "By Type": issue_df.groupby("Issue Type").size().to_dict(),
            "By Month": issue_df.groupby("Month").size().to_dict(),
            "By Priority": issue_df.groupby("Priority").size().to_dict(),
            "By Project": issue_df.groupby("Project Name").size().to_dict(),
            "By Status": issue_df.groupby("Current Status").size().to_dict()
        }

    def process_defect_summary(self, data_dict):
        """Aggregated metrics for Defect Summary."""
        issue_df = data_dict.get("Issue Summary", pd.DataFrame())
        worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
        release_df = data_dict.get("Release Summary", pd.DataFrame())

        if issue_df.empty:
            return pd.DataFrame()

        # Identify defects (Bugs)
        defects = issue_df[issue_df['Issue Type'].isin(['Bug', 'Defect'])].copy()
        
        if defects.empty:
            return pd.DataFrame()

        # Update: Fallback to Parent's Fix Version for Defects likely missing it
        # 1. Self-join issues to get Parent details
        if 'Parent Issue Key' in defects.columns and 'Fix Version' in issue_df.columns:
            # Create a simplified map of Key -> Fix Version AND Summary for potential parents
            # Check if Summary exists
            cols_to_fetch = ['Key', 'Fix Version']
            if 'Summary' in issue_df.columns:
                cols_to_fetch.append('Summary')
            
            parent_map = issue_df[cols_to_fetch].rename(columns={'Key': 'Parent Key', 'Fix Version': 'Parent Fix Version', 'Summary': 'Parent Issue Summary'})
            
            # Merge defects with parent info
            defects = defects.merge(parent_map, left_on='Parent Issue Key', right_on='Parent Key', how='left')
            
            # Fill logic
            def fill_fix_version(row):
                current_fv = str(row.get('Fix Version', ''))
                # Check directly for common empty indicators
                if pd.isna(row.get('Fix Version')) or current_fv.lower() in ['nan', 'none', '', 'no version']:
                    parent_fv = row.get('Parent Fix Version')
                    if not pd.isna(parent_fv) and str(parent_fv).lower() not in ['nan', 'none', '']:
                        return parent_fv
                return row.get('Fix Version')

            defects['Fix Version'] = defects.apply(fill_fix_version, axis=1)
            
            # Clean up temp columns
            defects.drop(columns=['Parent Key', 'Parent Fix Version'], inplace=True, errors='ignore')

        # Update: Fallback to Parent's Sprint for Defects likely missing it
        # CRITICAL FIX: 'Issue Summary' might only have 'Sprint ID'. We need 'Sprint Name'.
        sprint_df = data_dict.get("Sprint Summary", pd.DataFrame())
        target_sprint_col = 'Sprint Name'
        
        # Helper to map IDs if needed
        def ensure_sprint_name(df, source_id_col='Sprint ID'):
            if target_sprint_col not in df.columns and source_id_col in df.columns and not sprint_df.empty:
                # Map ID to Name
                id_to_name = sprint_df.set_index('Sprint ID')['Sprint Name'].to_dict()
                df[target_sprint_col] = df[source_id_col].map(id_to_name)
            return df

        # Enrich Defects with Sprint Name
        defects = ensure_sprint_name(defects)
        
        # Enrich Global Issue DF (for Parents) with Sprint Name
        # We work on a copy to not affect global state unexpectedly, or just map for the parents we need
        issue_df_enriched = ensure_sprint_name(issue_df.copy())
        
        if 'Parent Issue Key' in defects.columns and target_sprint_col in issue_df_enriched.columns:
             # Map Parent Key -> Sprint
            parent_sprint_map = issue_df_enriched[['Key', target_sprint_col]].rename(columns={'Key': 'Parent Key', target_sprint_col: 'Parent Sprint'})
            
            # Merge
            defects = defects.merge(parent_sprint_map, left_on='Parent Issue Key', right_on='Parent Key', how='left')
            
            def fill_sprint(row):
                current_sprint = str(row.get(target_sprint_col, ''))
                if pd.isna(row.get(target_sprint_col)) or current_sprint.lower() in ['nan', 'none', '']:
                    parent_sprint = row.get('Parent Sprint')
                    if not pd.isna(parent_sprint) and str(parent_sprint).lower() not in ['nan', 'none', '']:
                         return parent_sprint
                return row.get(target_sprint_col)

            defects[target_sprint_col] = defects.apply(fill_sprint, axis=1)
            defects.drop(columns=['Parent Key', 'Parent Sprint'], inplace=True, errors='ignore')

        # Join with Worklogs to get time spent per defect
        if not worklog_df.empty:
            defect_worklogs = worklog_df[worklog_df['Key'].isin(defects['Key'])]
            defect_time = defect_worklogs.groupby('Key')['Sum of Time Entry Log Time'].sum().reset_index()
            defects = defects.merge(defect_time, on='Key', how='left').fillna(0)
        else:
            defects['Sum of Time Entry Log Time'] = 0

        # Create aggregation by Release
        # Since an issue can have multiple fix versions (not in issue_df yet, but linked), we'll use a placeholder or join
        # For now, let's assume we want a summary dataframe
        
        return defects

    def process_worklog_summary(self, worklog_df):
        """Aggregates worklogs by author and month."""
        if worklog_df.empty:
            return pd.DataFrame(), []

        df = worklog_df.copy()
        
        # 1. Parse dates and normalize to naive UTC
        df['Time Entry Date'] = pd.to_datetime(df['Time Entry Date'], errors='coerce').dt.tz_localize(None)
        df = df.dropna(subset=['Time Entry Date'])
        
        # 2. Extract Month-Year (YYYY-MM for sorting, MMM-YY for display)
        df['SortMonth'] = df['Time Entry Date'].dt.to_period('M')
        df['Month-Year'] = df['Time Entry Date'].dt.strftime('%b-%y')
        
        # 3. Create Pivot Table
        pivot = df.pivot_table(
            index='Time Entry User',
            columns='SortMonth',
            values='Sum of Time Entry Log Time',
            aggfunc='sum'
        ).fillna(0)
        
        # 4. Convert columns from Period to MMM-YY for the pivot result
        month_map = {p: p.to_timestamp().strftime('%b-%y') for p in pivot.columns}
        pivot.rename(columns=month_map, inplace=True)
        
        # Get sorted list of display months
        sorted_months = [month_map[p] for p in sorted(pivot.columns.map(lambda x: next(k for k,v in month_map.items() if v==x)))]
        # Actually it's easier:
        sorted_display_months = [p.to_timestamp().strftime('%b-%y') for p in sorted(df['SortMonth'].unique())]
        
        # Add Total column
        pivot['Total Hours'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('Total Hours', ascending=False)
        
        return pivot.reset_index(), sorted_display_months

    def get_advanced_summary(self, data_dict):
        """Returns a high-level summary for the entire dashboard."""
        sprint_df = data_dict.get("Sprint Summary", pd.DataFrame())
        release_df = self.process_release_summary(data_dict)
        issue_df = data_dict.get("Issue Summary", pd.DataFrame())

        velocity = self.calculate_velocity(sprint_df)
        total_cost = release_df["Overall Release Cost ($)"].sum() if "Overall Release Cost ($)" in release_df.columns else 0
        total_issues = len(issue_df)

        return {
            "Average Velocity": velocity,
            "Total Estimated Cost": round(total_cost, 2),
            "Total Issues": total_issues,
            "Total Work Hours": round(release_df["Total work logged"].sum(), 2) if "Total work logged" in release_df.columns else 0
        }

    def process_role_metrics(self, data_dict, role, user=None):
        """Calculates specific KPIs for Developer, QA, and PO roles."""
        issue_df = data_dict.get("Issue Summary", pd.DataFrame())
        worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
        sprint_df = data_dict.get("Sprint Summary", pd.DataFrame())
        
        if issue_df.empty: return {}

        results = {}

        if role == "Developer":
            # Filter issues assigned to developer
            dev_issues = issue_df.copy()
            if user: dev_issues = dev_issues[dev_issues['Assignee Name'] == user]
            
            # 1. Total Story Points Completed
            sp_col = next((c for c in dev_issues.columns if any(x in c.lower() for x in ["story points", "story point", "completed sp"])), None)
            if sp_col:
                # Sum points only for Done/Resolved issues
                done_issues = dev_issues[dev_issues['Current Status'].str.lower().str.contains('done|closed|resolved', na=False)]
                results["Points Completed"] = done_issues[sp_col].sum()
            else:
                results["Points Completed"] = 0
            
            # 2. Throughput
            results["Stories Done"] = len(dev_issues[dev_issues['Current Status'].str.lower().str.contains('done|closed|resolved', na=False)])
            
            # 3. Efficiency (Hours/SP)
            total_hours = 0
            if not worklog_df.empty:
                wl = worklog_df.copy()
                if user: wl = wl[wl['Time Entry User'] == user]
                total_hours = wl["Sum of Time Entry Log Time"].sum()
            
            results["Total Hours"] = total_hours
            results["Efficiency (Hrs/SP)"] = round(total_hours / results["Points Completed"], 2) if results["Points Completed"] > 0 else 0
            
        elif role == "QA":
            qa_defects = issue_df[issue_df['Issue Type'].astype(str).str.lower().isin(['bug', 'defect'])].copy()
            if user: qa_defects = qa_defects[qa_defects['Reporter Name'] == user]
            
            results["Defects Identified"] = len(qa_defects)
            results["Critical Bugs"] = len(qa_defects[qa_defects['Priority'].astype(str).str.lower().str.contains('high|critical|blocker', na=False)])
            
            resolved = len(qa_defects[qa_defects['Current Status'].astype(str).str.lower().str.contains('done|closed|resolved', na=False)])
            results["Resolution Ratio"] = f"{(resolved/len(qa_defects)*100):.1f}%" if len(qa_defects) > 0 else "0%"
            
        elif role == "Product Owner":
            rel_df = data_dict.get("Release Summary", pd.DataFrame())
            results["Total Releases"] = len(rel_df['Fix Version'].unique()) if not rel_df.empty and 'Fix Version' in rel_df.columns else 0
            
            if not sprint_df.empty:
                comm_col = next((c for c in sprint_df.columns if "Committed Story Points" in c), None)
                comp_col = next((c for c in sprint_df.columns if "Completed Story Points" in c), None)
                total_comm = sprint_df[comm_col].sum() if comm_col else 0
                total_comp = sprint_df[comp_col].sum() if comp_col else 0
                results["Predictability (%)"] = f"{(total_comp/total_comm*100):.1f}%" if total_comm > 0 else "0%"
            
            total_bugs = len(issue_df[issue_df['Issue Type'].astype(str).str.lower().isin(['bug', 'defect'])])
            total_stories = len(issue_df[issue_df['Issue Type'].astype(str).str.contains('Story|Epic', case=False, na=False)])
            results["Defect Density"] = round(total_bugs / total_stories, 2) if total_stories > 0 else 0

        return results



    def process_non_compliance(self, data_dict, sprint_id=None, global_audit=False):
        """Calculates compliance rules for a specific sprint, active/future, or global audit."""
        issue_df = data_dict.get("Issue Summary", pd.DataFrame()).copy()
        sprint_df = data_dict.get("Sprint Summary", pd.DataFrame())
        
        rules = []

        if issue_df.empty:
            return rules

        # 1. Filter Logic
        if not global_audit and not sprint_df.empty:
            active_future_sprints = sprint_df[sprint_df['State'].str.lower().isin(['active', 'future'])]['Sprint ID'].tolist()
            if sprint_id:
                target_sprints = [sprint_id]
            else:
                target_sprints = active_future_sprints
            
            issue_df = issue_df[issue_df['Sprint ID'].isin(target_sprints)]
        
        # If global audit, keep all issues, but usually we care about non-resolved or recently resolved
        # User specified "all completed, in progress records", so we keep full issue_df.
        
        if issue_df.empty:
            return rules

        # Pre-calculate Last 3 Sprints Velocity for Capacity Overload check
        avg_velocity = 0
        if not sprint_df.empty:
            closed = sprint_df[sprint_df['State'].str.lower() == 'closed']
            # Sort by Complete Date or ID to get most recent
            if 'Complete Date' in closed.columns and not closed['Complete Date'].isna().all():
                closed = closed.sort_values('Complete Date', ascending=False)
            else:
                closed = closed.sort_values('Sprint ID', ascending=False)
            
            if not closed.empty and 'Total of Completed Story Points' in closed.columns:
                avg_velocity = closed.head(3)['Total of Completed Story Points'].mean()

        # Story Point column
        sp_col = next((c for c in issue_df.columns if any(x in c.lower() for x in ["story points", "story point", "completed sp"])), None)


        
        # Rule Helper
        def add_rule(name, issues):
            if issues.empty:
                keys = []
            else:
                try:
                    # Unique and sort keys to avoid duplicates in summary
                    keys = sorted(list(set(issues['Key'].tolist())))
                except KeyError:
                    keys = []
                    
            score = "Green" if len(keys) == 0 else "Red"
            rules.append({
                "Compliance CheckPoint": name,
                "Compliance Score": score,
                "Issue keys": ", ".join(keys) if keys else "-"
            })

        # 1. Story Points Missing
        if sp_col:
            missing_sp = issue_df[pd.isna(issue_df[sp_col]) | (issue_df[sp_col] == 0)]
            # Usually only stories/tasks need points
            missing_sp = missing_sp[issue_df['Issue Type'].str.lower().str.contains('story|task', na=False)]
            add_rule("Story Points Missing", missing_sp)
        else:
            add_rule("Story Points Missing", issue_df)

        # 2. No Assignee
        no_assignee = issue_df[pd.isna(issue_df['Assignee Name'])]
        add_rule("No Assignee", no_assignee)

        # 3. Parent / Epic Linked Missing
        missing_link = issue_df[pd.isna(issue_df['Epic Link']) & pd.isna(issue_df['Parent Issue Key'])]
        # Exclude Epics themselves from this check
        missing_link = missing_link[missing_link['Issue Type'].str.lower() != 'epic']
        add_rule("Parent / Epic Linked Missing", missing_link)

        # 4. Acceptance Criteria Missing
        missing_ac = issue_df[pd.isna(issue_df['Acceptance Criteria']) | (issue_df['Acceptance Criteria'].astype(str).str.strip() == "")]
        # Only for Stories
        missing_ac = missing_ac[missing_ac['Issue Type'].str.lower().str.contains('story', na=False)]
        add_rule("Acceptance Criteria Missing", missing_ac)

        # 5. Description Incomplete
        def is_short(d):
            if pd.isna(d): return True
            return len(str(d).strip()) < 50
        incomplete_desc = issue_df[issue_df['Description'].apply(is_short)]
        add_rule("Description Incomplete", incomplete_desc)

        # 6. Priority Missing
        missing_prio = issue_df[pd.isna(issue_df['Priority'])]
        add_rule("Priority Missing", missing_prio)

        # 7. Fix Version / Release Missing
        missing_version = issue_df[pd.isna(issue_df['Fix Version']) | (issue_df['Fix Version'] == "No Version")]
        add_rule("Fix Version / Release Missing", missing_version)

        # 8. Sprint Capacity Overload
        if sprint_id and sp_col:
            sprint_total = issue_df[sp_col].sum()
            if sprint_total > avg_velocity and avg_velocity > 0:
                rules.append({
                    "Compliance CheckPoint": "Sprint Capacity Overload",
                    "Compliance Score": "Red",
                    "Issue keys": f"Total SP ({int(sprint_total)}) > Avg Velocity ({int(avg_velocity)})"
                })
            else:
                rules.append({
                    "Compliance CheckPoint": "Sprint Capacity Overload",
                    "Compliance Score": "Green",
                    "Issue keys": f"Total SP ({int(sprint_total)}) <= Avg Velocity ({int(avg_velocity)})" if avg_velocity > 0 else "-"
                })

        # 9. Epic Completed but Open
        epic_df = data_dict.get("Epic Summary", pd.DataFrame())
        if not epic_df.empty and 'Epic Status' in epic_df.columns:
            # Check for Completed but not Done
            # Condition: Total Stories == Completed Stories (and > 0) AND Status != Done
            
            # Helper to check completeness
            def is_complete_but_open(row):
                status = str(row['Epic Status']).lower()
                if status in ['done', 'closed', 'resolved']:
                    return False
                
                total = row.get('Total Stories Count', 0)
                completed = row.get('Completed Stories Count', 0)
                
                # Treat NaN as 0
                total = 0 if pd.isna(total) else total
                completed = 0 if pd.isna(completed) else completed
                
                if total > 0 and total == completed:
                    return True
                return False

            open_completed_epics = epic_df[epic_df.apply(is_complete_but_open, axis=1)]
            
            if not open_completed_epics.empty:
                 rules.append({
                    "Compliance CheckPoint": "Epic Completed but Open",
                    "Compliance Score": "Red",
                    "Issue keys": ", ".join(open_completed_epics['Epic Key'].tolist())
                })
            else:
                 rules.append({
                    "Compliance CheckPoint": "Epic Completed but Open",
                    "Compliance Score": "Green",
                    "Issue keys": "-"
                })

        # 10. Defect in Progress / Parent No Sprint
        # Condition: Defect is In Progress AND Parent has NO Sprint
        sprint_col = 'Sprint Name' if 'Sprint Name' in issue_df.columns else 'Sprint'
        
        # 1. Get In Progress Defects
        ip_status = ['in progress', 'in development', 'dev. in progress', 'in review', 'in qa', 'in analysis']
        ip_defects = issue_df[
            (issue_df['Issue Type'].isin(['Bug', 'Defect'])) & 
            (issue_df['Current Status'].str.lower().isin(ip_status))
        ].copy()

        if not ip_defects.empty and 'Parent Issue Key' in ip_defects.columns:
            # 2. Get Parent Info (Need Global mapping as parent might not be in the "Active Sprint" filtered issue_df if not assigned)
            # Actually process_non_compliance receives full Issue Summary usually, but it filters it at the start.
            # Use raw data for parent lookup to be safe
            raw_issue_df = data_dict.get("Issue Summary", pd.DataFrame())
            
            if not raw_issue_df.empty and sprint_col in raw_issue_df.columns:
                 parent_sprints = raw_issue_df[['Key', sprint_col]].rename(columns={'Key': 'Parent Key', sprint_col: 'Parent Sprint'})
                 
                 merged = ip_defects.merge(parent_sprints, left_on='Parent Issue Key', right_on='Parent Key', how='left')
                 
                 # Check for Empty Parent Sprint
                 def is_orphan(row):
                     ps = str(row['Parent Sprint']).lower()
                     if pd.isna(row['Parent Sprint']) or ps in ['nan', 'none', '']:
                         return True
                     return False
                 
                 orphaned_defects = merged[merged.apply(is_orphan, axis=1)]
                 
                 add_rule("Defect In Progress (Parent has No Sprint)", orphaned_defects)
            else:
                 # Fallback if raw data issue or no parent column
                 add_rule("Defect In Progress (Parent has No Sprint)", pd.DataFrame())

        # 11. Done Stories with No Worklog
        # Condition: Status is DONE + Total Effort (Story + Subtasks) == 0
        
        # 1. Identify Done Stories
        done_keywords = ['done', 'closed', 'resolved', 'released']
        done_stories = issue_df[
            (issue_df['Issue Type'].astype(str).str.lower() == 'story') &
            (issue_df['Current Status'].astype(str).str.lower().isin(done_keywords))
        ].copy()

        if not done_stories.empty:
            # 2. Calculate Effort
            # We need to sum "Sum of Time Entry Log Time" from Worklog Summary for the Story AND its Sub-tasks
            worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
            
            if not worklog_df.empty:
                # Group worklogs by Key
                wl_summ = worklog_df.groupby('Key')['Sum of Time Entry Log Time'].sum().reset_index()
                
                # We need Sub-task linkage. Use raw Issue Summary for full hierarchy (in case subtasks are filtered out of current view)
                raw_issue_df = data_dict.get("Issue Summary", pd.DataFrame())
                if not raw_issue_df.empty:
                    # Map Subtask -> Parent
                    subtasks = raw_issue_df[raw_issue_df['Issue Type'].astype(str).str.lower() == 'sub-task'][['Key', 'Parent Issue Key']]
                    
                    # Merge Worklog into Subtasks
                    subtasks = subtasks.merge(wl_summ, on='Key', how='left').fillna(0)
                    
                    # Rollup Subtask Worklogs to Parent
                    subtask_effort = subtasks.groupby('Parent Issue Key')['Sum of Time Entry Log Time'].sum().reset_index()
                    subtask_effort.rename(columns={'Sum of Time Entry Log Time': 'Subtask Effort', 'Parent Issue Key': 'Key'}, inplace=True)
                    
                    # Merge Direct Worklogs for Story
                    story_effort = wl_summ.rename(columns={'Sum of Time Entry Log Time': 'Direct Effort'})
                    
                    # Merge everything into Done Stories
                    done_stories = done_stories.merge(story_effort, on='Key', how='left')
                    done_stories = done_stories.merge(subtask_effort, on='Key', how='left')
                    
                    done_stories['Direct Effort'] = done_stories['Direct Effort'].fillna(0)
                    done_stories['Subtask Effort'] = done_stories['Subtask Effort'].fillna(0)
                    done_stories['Total Effort'] = done_stories['Direct Effort'] + done_stories['Subtask Effort']
                    
                    # Filter for 0 Effort
                    zero_effort_stories = done_stories[done_stories['Total Effort'] == 0]
                    add_rule("Done Stories with No Worklog", zero_effort_stories)
                else:
                    # Fallback if no hierarchy info
                    add_rule("Done Stories with No Worklog", pd.DataFrame())
            else:
                 # If no worklogs exist at all, ALL done stories are non-compliant
                 add_rule("Done Stories with No Worklog", done_stories)
        else:
             add_rule("Done Stories with No Worklog", pd.DataFrame())

        # 12. Late Logs on Completed Issues (>15d Backdated)
        backdated_logs = self.process_backdated_worklogs(data_dict)
        add_rule("Late Logs on Completed Issues (>15d Backdated)", backdated_logs)
        if not backdated_logs.empty:
            users = ", ".join(sorted(backdated_logs['Time Entry User'].unique()))
            hrs = f"{backdated_logs['Hours Added'].sum():.1f} hrs"
            rules.append({"Compliance CheckPoint": "Late Logs - Users Involved", "Compliance Score": "Red", "Issue keys": users})
            rules.append({"Compliance CheckPoint": "Late Logs - Total Hours Added", "Compliance Score": "Red", "Issue keys": hrs})
        else:
            rules.append({"Compliance CheckPoint": "Late Logs - Users Involved", "Compliance Score": "Green", "Issue keys": "-"})
            rules.append({"Compliance CheckPoint": "Late Logs - Total Hours Added", "Compliance Score": "Green", "Issue keys": "-"})

        # 13. Worklogs After Release Completion
        try:
            release_summary_raw = data_dict.get("Release Summary", pd.DataFrame())
            worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
            
            # Check for required columns
            rel_cols = ["Fix Version", "End Date", "Released"]
            has_rel_cols = all(c in release_summary_raw.columns for c in rel_cols) if not release_summary_raw.empty else False
            
            if not release_summary_raw.empty and not worklog_df.empty and has_rel_cols:
                # Create mapping of Fix Version -> End Date ONLY for Released versions
                released_df = release_summary_raw[release_summary_raw["Released"] == True]
                rel_dates = released_df[["Fix Version", "End Date"]].dropna().set_index("Fix Version")["End Date"].to_dict()
                
                # Mapping of Key -> Fix Version
                full_issue_df = data_dict.get("Issue Summary", pd.DataFrame())
                issue_versions = full_issue_df.set_index("Key")["Fix Version"].to_dict() if not full_issue_df.empty else {}
                
                late_rel_logs = []
                for _, wl in worklog_df.iterrows():
                    ikey = wl.get("Key")
                    version = issue_versions.get(ikey)
                    if version and version in rel_dates:
                        try:
                            # Robust date parsing and comparison - strip timezone consistently
                            wl_dt = pd.to_datetime(wl.get("Time Entry Date"))
                            if wl_dt.tzinfo is not None:
                                wl_dt = wl_dt.replace(tzinfo=None)
                            
                            rel_dt = pd.to_datetime(rel_dates[version])
                            if rel_dt.tzinfo is not None:
                                rel_dt = rel_dt.replace(tzinfo=None)
                                
                            rel_dt = rel_dt.replace(hour=23, minute=59, second=59)
                            if wl_dt > rel_dt:
                                late_rel_logs.append(wl)
                        except:
                            continue
                
                if late_rel_logs:
                    late_rel_df = pd.DataFrame(late_rel_logs)
                    add_rule("Logs After Release Completion", late_rel_df)
                    users_involved = ", ".join(sorted(late_rel_df['Time Entry User'].map(str).unique()))
                    issue_count = f"{len(late_rel_df['Key'].unique())} Issues"
                    rules.append({"Compliance CheckPoint": "Logs After Release - Users Involved", "Compliance Score": "Red", "Issue keys": users_involved})
                    rules.append({"Compliance CheckPoint": "Logs After Release - Issue Count", "Compliance Score": "Red", "Issue keys": issue_count})
                else:
                    add_rule("Logs After Release Completion", pd.DataFrame())
            else:
                add_rule("Logs After Release Completion", pd.DataFrame())
        except Exception as e:
            rules.append({"Compliance CheckPoint": "Error in Release Compliance Rule", "Compliance Score": "Red", "Issue keys": str(e)})

        return rules

    def get_weekly_worklog_stats(self, data_dict):
        """Calculates weekly worklog stats for compliance."""
        worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
        if worklog_df.empty:
            return pd.DataFrame()
        
        df = worklog_df.copy()
        df['Time Entry Date'] = pd.to_datetime(df['Time Entry Date'], errors='coerce')
        
        # Determine "Last Week" (Mon-Sun of previous week relative to today)
        today = pd.Timestamp.now().normalize()
        current_week_start = today - pd.Timedelta(days=today.dayofweek)
        last_week_start = current_week_start - pd.Timedelta(weeks=1)
        last_week_end = current_week_start 
        
        # Filter
        mask = (df['Time Entry Date'] >= last_week_start) & (df['Time Entry Date'] < last_week_end)
        weekly_df = df[mask]
        
        if weekly_df.empty:
            return pd.DataFrame(columns=["User", "Total Hours", "Status"])
            
        stats = weekly_df.groupby("Time Entry User")["Sum of Time Entry Log Time"].sum().reset_index()
        stats.columns = ["User", "Total Hours"]
        
        def get_status(hours):
            return "Low Code (< 40h)" if hours < 40 else "Compliant"
            
        stats["Status"] = stats["Total Hours"].apply(get_status)
        return stats

    def process_backdated_worklogs(self, data_dict):
        """Identifies worklogs added after issue resolution with >15 day backdate."""
        issue_df = data_dict.get("Issue Summary", pd.DataFrame())
        worklog_df = data_dict.get("Worklog Summary", pd.DataFrame())
        
        if issue_df.empty or worklog_df.empty:
            return pd.DataFrame()
            
        # Ensure we have necessary columns
        if 'Resolution Date' not in issue_df.columns:
            return pd.DataFrame()
            
        # Filter issues that are resolved
        resolved_issues = issue_df.dropna(subset=['Resolution Date']).copy()
        resolved_issues['Resolution Date'] = pd.to_datetime(resolved_issues['Resolution Date'], errors='coerce').dt.tz_localize(None)
        
        # Merge with worklogs on Key
        merged = worklog_df.merge(resolved_issues[['Key', 'Resolution Date']], on='Key', how='inner')
        
        if merged.empty:
            return pd.DataFrame()
            
        # Parse Dates
        merged['Time Entry Date'] = pd.to_datetime(merged['Time Entry Date'], errors='coerce').dt.tz_localize(None)
        merged['Worklog Creation Date'] = pd.to_datetime(merged['Worklog Creation Date'], errors='coerce').dt.tz_localize(None)
        
        # Drop NaNs
        merged = merged.dropna(subset=['Time Entry Date', 'Worklog Creation Date', 'Resolution Date'])
        
        # Calculate Backdate
        merged['Backdate Days'] = (merged['Worklog Creation Date'] - merged['Time Entry Date']).dt.days
        
        # Filter Conditions: 
        # 1. Activity after Resolution
        # 2. Backdate > 15 days
        flags = merged[
            (merged['Time Entry Date'] > merged['Resolution Date']) & 
            (merged['Backdate Days'] > 15)
        ].copy()
        
        if flags.empty:
            return pd.DataFrame()
            
        # Format Results
        results = flags[[
            'Key', 'Time Entry User', 'Sum of Time Entry Log Time', 
            'Time Entry Date', 'Worklog Creation Date', 'Backdate Days'
        ]].rename(columns={
            'Sum of Time Entry Log Time': 'Hours Added',
            'Time Entry Date': 'Work Date',
            'Worklog Creation Date': 'Logged Date'
        })
        
        # Sort by Logged Date (newest first)
        return results.sort_values('Logged Date', ascending=False)
