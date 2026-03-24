import pandas as pd
from jira_client import JiraClient

class IssueSummaryExtractor:
    def __init__(self, client: JiraClient, sprint_field='customfield_10020', sp_field='customfield_10033'):
        self.client = client
        self.sprint_field = sprint_field
        self.sp_field = sp_field

    def extract(self, updated_since=None, project_key=None, jql_filter=None):
        # We need to fetch all issues.
        jql_parts = []
        if jql_filter:
            jql_parts.append(f"({jql_filter})")
        elif project_key:
            jql_parts.append(f'project = "{project_key}"')
            
        if updated_since:
            jql_parts.append(f'updated >= "{updated_since}"')
            
        jql = " AND ".join(jql_parts)
        if jql:
            jql += " "
        jql += "order by updated desc"
        
        print(f"DEBUG: Issue JQL: {jql}", flush=True)
            
        fields = f"key,issuetype,priority,status,created,resolutiondate,duedate,customfield_10014,parent,project,reporter,assignee,sprint,{self.sprint_field},{self.sp_field},labels,components,fixVersions,description,customfield_10036"
        issues = self.client.get_all_paginated("search", params={"jql": jql, "fields": fields})
        
        issue_data = []
        for issue in issues:
            f = issue['fields']
            parent = f.get('parent')
            project = f.get('project', {})
            sprint = f.get(self.sprint_field) or f.get('sprint')
            sprint_id = None
            if sprint:
                sprint_id = sprint[0].get('id') if isinstance(sprint, list) else sprint.get('id')

            # Extract Fix Version
            fix_versions = f.get('fixVersions', [])
            fix_version_name = fix_versions[0].get('name') if fix_versions else "No Version"

            issue_data.append({
                "Key": issue['key'],
                "Issue Type": (f.get('issuetype') or {}).get('name'),
                "Priority": (f.get('priority') or {}).get('name'),
                "Current Status": (f.get('status') or {}).get('name'),
                "Created Date": f.get('created'),
                "Resolution Date": f.get('resolutiondate'),
                "Due Date": f.get('duedate'),
                "Epic Link": f.get('customfield_10014'), 
                "Parent Issue Key": parent.get('key') if parent else None,
                "Parent Issue Type": (parent.get('fields', {}).get('issuetype') or {}).get('name') if parent else None,
                "Parent Issue Summary": parent.get('fields', {}).get('summary') if parent else None,
                "Parent Issue Status": (parent.get('fields', {}).get('status') or {}).get('name') if parent else None,
                "Parent Issue Priority": (parent.get('fields', {}).get('priority') or {}).get('name') if parent else None,
                "Project Category": (project.get('projectCategory') or {}).get('name'),
                "Project Name": project.get('name'),
                "Project Key": project.get('key'),
                "Reporter Name": (f.get('reporter') or {}).get('displayName'),
                "Assignee Name": (f.get('assignee') or {}).get('displayName') if f.get('assignee') else None,
                "Sprint ID": sprint_id,
                "Fix Version": fix_version_name,
                "Story Points": f.get(self.sp_field),
                "Description": f.get('description'),
                "Acceptance Criteria": f.get('customfield_10036')
            })

        df = pd.DataFrame(issue_data)
        if df.empty:
            # Ensure columns exist even if no data
            return pd.DataFrame(columns=[
                "Key", "Issue Type", "Priority", "Current Status", "Created Date", 
                "Resolution Date", "Due Date", "Epic Link", "Parent Issue Key", 
                "Parent Issue Type", "Parent Issue Summary", "Parent Issue Status", 
                "Parent Issue Priority", "Project Category", "Project Name", 
                "Project Key", "Reporter Name", "Assignee Name", "Sprint ID", "Fix Version", "Story Points"
            ])
        return df

if __name__ == "__main__":
    client = JiraClient()
    extractor = IssueSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
