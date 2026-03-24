import pandas as pd
from jira_client import JiraClient

class WorklogSummaryExtractor:
    def __init__(self, client: JiraClient):
        self.client = client

    def get_all_issue_keys(self, project_key=None):
        # We need all issues that might have worklogs.
        jql = 'timespent > 0'
        if project_key:
            jql += f' AND project = "{project_key}"'
        return self.client.get_all_paginated("search", params={"jql": jql, "fields": "key"})

    def get_issue_worklogs(self, issue_key):
        return self.client.get(f"issue/{issue_key}/worklog")

    def extract(self, project_key=None, updated_since=None, jql_filter=None):
        # Optimization: Fetch issues with worklogs expanded in search results
        jql = 'timespent > 0'
        if jql_filter:
            jql += f' AND ({jql_filter})'
        elif project_key:
            jql += f' AND project = "{project_key}"'
        if updated_since:
            jql += f' AND updated >= "{updated_since}"'
            
        print(f"DEBUG: Bulk fetching issues and worklogs for {project_key or 'all'} (Updated >= {updated_since})...", flush=True)
        params = {"jql": jql, "fields": "key,worklog,project,issuetype", "expand": "worklog"}
        issues = self.client.get_all_paginated("search", params=params)
        
        worklog_data = []
        total_issues = len(issues)
        issues_needing_individual_fetch = 0
        
        for i, issue in enumerate(issues):
            key = issue['key']
            f = issue.get('fields', {})
            project = f.get('project', {})
            issue_type = (f.get('issuetype') or {}).get('name')
            project_category = (project.get('projectCategory') or {}).get('name', 'No Category')
            project_name = project.get('name')
            project_type = project.get('projectTypeKey')

            worklog_container = f.get('worklog', {})
            worklogs = worklog_container.get('worklogs', [])
            total_wl_count = worklog_container.get('total', 0)
            
            # If the search response didn't include all worklogs (usually capped at 20), fetch individually
            if len(worklogs) < total_wl_count:
                issues_needing_individual_fetch += 1
                if issues_needing_individual_fetch % 10 == 0:
                    print(f"DEBUG: [{i+1}/{total_issues}] Fetching full worklogs for {key} (truncated in search)...", flush=True)
                worklogs_resp = self.get_issue_worklogs(key)
                worklogs = worklogs_resp.get('worklogs', [])

            for wl in worklogs:
                worklog_data.append({
                    "Key": key,
                    "Issue Type": issue_type,
                    "Project Name": project_name,
                    "Project Type": project_type,
                    "Project Category": project_category,
                    "Time Entry Date": wl.get('started'),
                    "Sum of Time Entry Log Time": wl.get('timeSpentSeconds', 0) / 3600, # In hours
                    "Time Entry User": (wl.get('author') or {}).get('displayName'),
                    "Worklog Creation Date": wl.get('created'),
                    "Worklog ID": wl.get('id'),
                    "Worklog Last Updation Date": wl.get('updated')
                })

        print(f"DEBUG: Completed worklog extraction. Fetched {len(worklog_data)} entries. {issues_needing_individual_fetch} issues required extra API calls.", flush=True)
        return pd.DataFrame(worklog_data)

if __name__ == "__main__":
    client = JiraClient()
    extractor = WorklogSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
