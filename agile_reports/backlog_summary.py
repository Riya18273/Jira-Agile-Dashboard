import pandas as pd
from datetime import datetime
from jira_client import JiraClient

class BacklogSummaryExtractor:
    def __init__(self, client: JiraClient, sp_field='customfield_10033'):
        self.client = client
        self.sp_field = sp_field

    def extract(self, project_key=None):
        if not project_key:
            print("ERROR: Project Key is required for Backlog extraction.")
            return pd.DataFrame()

        print(f"DEBUG: Fetching unsprinted backlog for project {project_key}...", flush=True)
        # JQL: Not in sprint and not done
        jql = f'project = "{project_key}" AND sprint is EMPTY AND statusCategory != "Done"'
        fields = f"key,issuetype,priority,status,created,updated,assignee,{self.sp_field}"
        
        issues = self.client.get_all_paginated("search", params={"jql": jql, "fields": fields})
        print(f"DEBUG: Found {len(issues)} items in the unsprinted backlog.", flush=True)

        backlog_data = []
        now = datetime.now()

        for issue in issues:
            f = issue.get('fields', {})
            created_date = f.get('created')
            age_days = None
            if created_date:
                # Jira date format: 2024-04-15T10:09:13.603+0530
                try:
                    dt = datetime.strptime(created_date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    age_days = (now - dt).days
                except:
                    pass

            backlog_data.append({
                "Key": issue['key'],
                "Issue Type": (f.get('issuetype') or {}).get('name'),
                "Priority": (f.get('priority') or {}).get('name'),
                "Status": (f.get('status') or {}).get('name'),
                "Story Points": f.get(self.sp_field),
                "Created Date": created_date,
                "Updated Date": f.get('updated'),
                "Age (Days)": age_days,
                "Assignee": (f.get('assignee') or {}).get('displayName', 'Unassigned'),
                "Backlog Category": "Unplanned" if age_days and age_days > 30 else "Recent"
            })

        return pd.DataFrame(backlog_data)
