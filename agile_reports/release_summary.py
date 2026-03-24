import pandas as pd
from jira_client import JiraClient
from datetime import datetime

class ReleaseSummaryExtractor:
    def __init__(self, client: JiraClient, sp_field='customfield_10033'):
        self.client = client
        self.sp_field = sp_field

    def get_projects(self):
        return self.client.get("project")

    def get_versions(self, project_key):
        return self.client.get(f"project/{project_key}/versions")

    def get_version_issues(self, version_id):
        jql = f'fixVersion = {version_id}'
        # Get issues directly associated with the version
        fields = f"key,issuetype,status,{self.sp_field},sprint,worklog"
        return self.client.get_all_paginated("search", params={"jql": jql, "fields": fields, "expand": "worklog"})

    def get_all_worklogs(self, issue_key):
        """Fetches all worklogs for an issue with full pagination."""
        worklogs = []
        start_at = 0
        max_results = 100
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            data = self.client.get(f"issue/{issue_key}/worklog", params=params)
            if not data or 'worklogs' not in data:
                break
            entries = data.get('worklogs', [])
            worklogs.extend(entries)
            total = data.get('total', 0)
            if len(entries) < max_results or len(worklogs) >= total:
                break
            start_at += len(entries)
        return worklogs

    def get_child_worklogs(self, parent_keys):
        """Fetches hierarchical children (Sub-tasks, SDT, TCC, TCE, Defects) using JQL."""
        if not parent_keys:
            return []
        
        results = []
        batch_size = 50
        for i in range(0, len(parent_keys), batch_size):
            batch = parent_keys[i:i + batch_size]
            keys_str = ",".join([f'"{k}"' for k in batch])
            jql = f"parent in ({keys_str})"
            fields = "key,worklog,issuetype,status" 
            batch_data = self.client.get_all_paginated("search", params={"jql": jql, "fields": fields, "expand": "worklog"})
            results.extend(batch_data)
        return results

    def extract(self, project_key=None, jql_filter=None):
        projects = self.get_projects()
        release_data = []

        target_keys = set()
        if project_key:
            target_keys.add(project_key)
        elif jql_filter:
            # Robust JQL Project Key Extraction
            # Handles: project in (A, B), project=A, project = "A"
            import re
            
            # 1. project in (...)
            match_in = re.search(r'project\s+in\s*\((.*?)\)', jql_filter, re.IGNORECASE)
            if match_in:
                 keys_str = match_in.group(1)
                 target_keys.update({k.strip().strip('"').strip("'") for k in keys_str.split(',')})
            
            # 2. project = X
            if not target_keys:
                match_eq = re.search(r'project\s*=\s*["\']?([\w\d]+)["\']?', jql_filter, re.IGNORECASE)
                if match_eq:
                    target_keys.add(match_eq.group(1))

        print(f"DEBUG: Processing Release Summary for Projects: {target_keys}", flush=True)

        for project in projects:
            p_key = project.get('key')
            if not p_key:
                continue
            p_name = project.get('name') or p_key
            
            # Filter Logic
            if target_keys and p_key not in target_keys:
                continue
                
            print(f"DEBUG: Fetching Versions for {p_key}", flush=True)
            versions = self.get_versions(p_key)

            for version in versions:
                version_id = version['id']
                version_name = version['name']
                import re
                version_name = version['name']
                # Remove "patch" suffix and anything after it (e.g., -Patch1,  patch)
                match = re.search(r'[\s-]*patch', version_name, re.IGNORECASE)
                if match:
                    version_name = version_name[:match.start()].strip()
                issues = self.get_version_issues(version_id)
                if not issues:
                    continue

                v_stats = {
                    "sp_planned": 0.0, "sp_completed": 0.0,
                    "total_issues": 0, "completed_issues": 0,
                    "stories_planned": 0, "stories_completed": 0,
                    "features_planned": 0, "features_completed": 0,
                    "total_defects": 0, "completed_defects": 0,
                    "test_cases_executed": 0
                }
                user_total_hours = {}
                total_work_logged = 0

                # Identify all children (2 levels deep)
                issues_keys = [issue['key'] for issue in issues]
                level1_children = self.get_child_worklogs(issues_keys)
                level1_keys = [c['key'] for c in level1_children]
                level2_children = self.get_child_worklogs(level1_keys)
                
                all_ids = {issue['key'] for issue in issues}
                unique_children = []
                for child in (level1_children + level2_children):
                    if child['key'] not in all_ids:
                        unique_children.append(child)
                        all_ids.add(child['key'])
                
                all_relevant_issues = issues + unique_children
                print(f"DEBUG: Rel '{version_name}' - Parents: {len(issues)}, Children: {len(unique_children)}", flush=True)

                start_dt_str = version.get('startDate')
                end_dt_str = version.get('releaseDate') # releaseDate is typically used as End Date
                
                rel_start = pd.to_datetime(start_dt_str).tz_localize(None) if start_dt_str else pd.Timestamp("2000-01-01")
                rel_end = pd.to_datetime(end_dt_str).tz_localize(None) if end_dt_str else pd.Timestamp("2100-01-01")
                # Set end of day for rel_end
                rel_end = rel_end.replace(hour=23, minute=59, second=59)

                for issue in all_relevant_issues:
                    issue_key = issue['key']
                    f = issue['fields']
                    is_direct = issue_key in {i['key'] for i in issues}
                    
                    i_type = (f.get('issuetype') or {}).get('name', '').lower()
                    i_type_full = (f.get('issuetype') or {}).get('name', '')
                    
                    # 1. Worklogs (Aggregate logs within release date range)
                    w_container = f.get('worklog', {})
                    w_entries = w_container.get('worklogs', [])
                    total_wl_count = w_container.get('total', 0)
                    
                    # Robust pagination check
                    if len(w_entries) < total_wl_count:
                        w_entries = self.get_all_worklogs(issue_key)

                    for wl in w_entries:
                        author = wl.get('author', {}).get('displayName', 'Unknown')
                        wl_date_str = wl.get('started')
                        
                        try:
                            # Use pandas for robust date parsing
                            # Convert to UTC and then make naive for comparison
                            wl_dt = pd.to_datetime(wl_date_str, utc=True).tz_convert(None)
                            
                            # Filter by Release Dates
                            if rel_start <= wl_dt <= rel_end:
                                hrs = wl.get('timeSpentSeconds', 0) / 3600
                                user_total_hours[author] = user_total_hours.get(author, 0) + hrs
                                total_work_logged += hrs
                        except Exception:
                            # Fallback: Count if date parsing fails
                            hrs = wl.get('timeSpentSeconds', 0) / 3600
                            user_total_hours[author] = user_total_hours.get(author, 0) + hrs
                            total_work_logged += hrs

                    # 2. Metrics 
                    # Note: We count Defects and Test Cases even if they are sub-tasks (inherited metrics)
                    # Feature and Story counts are typically direct issues tagged with the version
                    is_done = (f.get('status') or {}).get('statusCategory', {}).get('key') == 'done'
                    is_story = i_type in ['story', 'user story']
                    is_bug = i_type in ['bug', 'defect']
                    is_feature = i_type in ['feature']
                    is_test_exec = i_type in ['sdt', 'tce', 'tcc', 'test case', 'test execution']

                    if is_direct:
                        v_stats["total_issues"] += 1
                        if is_done: v_stats["completed_issues"] += 1

                        sp = float(f.get(self.sp_field) or 0)
                        v_stats["sp_planned"] += sp
                        if is_done: v_stats["sp_completed"] += sp

                        if is_story:
                            v_stats["stories_planned"] += 1
                            if is_done: v_stats["stories_completed"] += 1
                        
                        if is_feature:
                            v_stats["features_planned"] += 1
                            if is_done: v_stats["features_completed"] += 1

                    # Defect and Test Exec counts typically include children if they are of that type
                    if is_bug:
                        v_stats["total_defects"] += 1
                        if is_done: v_stats["completed_defects"] += 1
                    
                    if is_test_exec:
                        v_stats["test_cases_executed"] += 1

                # Headcount: Users logged > 8 hours
                headcount_users = [u for u, h in user_total_hours.items() if h >= 8]
                headcount = len(headcount_users)
                user_breakdown = ", ".join([f"{u} ({round(h, 1)}h)" for u, h in sorted(user_total_hours.items(), key=lambda x: x[1], reverse=True)])

                release_data.append({
                    "Project Key": p_key,
                    "Project Name": p_name,
                    "Fix Version": version_name,
                    "Start Date": version.get('startDate'),
                    "End Date": version.get('releaseDate'),
                    "Released": version.get('released'),
                    "Release Status": "Released" if version.get('released') else "Unreleased",
                    "Feature Planned": v_stats["features_planned"],
                    "Feature completed": v_stats["features_completed"],
                    "User Story Planned": v_stats["stories_planned"],
                    "User Story Completed": v_stats["stories_completed"],
                    "Story Points Committed": v_stats["sp_planned"],
                    "Story Points Completed": v_stats["sp_completed"],
                    "Story Points Remaining": v_stats["sp_planned"] - v_stats["sp_completed"],
                    "Total Issues": v_stats["total_issues"],
                    "Total Completed Issues": v_stats["completed_issues"],
                    "Total Defect": v_stats["total_defects"],
                    "Total Test Case Executed": v_stats["test_cases_executed"],
                    "Head Count": headcount,
                    "Total work logged": round(total_work_logged, 2),
                    "Users Logged > 8h": ", ".join(headcount_users),
                    "Full Worklog Breakdown": user_breakdown
                })

        return pd.DataFrame(release_data)

if __name__ == "__main__":
    client = JiraClient()
    extractor = ReleaseSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
