import pandas as pd
from jira_client import JiraClient

class TransitionHistoryExtractor:
    def __init__(self, client: JiraClient):
        self.client = client

    def extract(self, project_key=None):
        print(f"DEBUG: Extracting transition history for project {project_key}...")
        
        jql = f'project = "{project_key}"' if project_key else "order by updated desc"
        # We need changelog expand to get transitions
        # Note: get_all_paginated handles normal search, but we need to ensure expand is passed
        issues = self.client.get_all_paginated("search", params={
            "jql": jql, 
            "fields": "key", 
            "expand": "changelog"
        })
        
        transitions = []
        for issue in issues:
            key = issue.get('key')
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            
            for h in histories:
                created = h.get('created')
                author = h.get('author', {}).get('displayName')
                h_id = h.get('id')
                
                items = h.get('items', [])
                for item in items:
                    if item.get('field') == 'status':
                        transitions.append({
                            "Issue Key": key,
                            "Transition Date": created,
                            "From Status": item.get('fromString'),
                            "To Status": item.get('toString'),
                            "Author": author,
                            "History ID": h_id
                        })
        
        df = pd.DataFrame(transitions)
        if df.empty:
            return pd.DataFrame(columns=["Issue Key", "Transition Date", "From Status", "To Status", "Author", "History ID"])
            
        # Sort by key and date for easier Power BI processing
        df = df.sort_values(by=["Issue Key", "Transition Date"])
        return df

if __name__ == "__main__":
    client = JiraClient()
    extractor = TransitionHistoryExtractor(client)
    df = extractor.extract(project_key="M5R")
    print(df.head())
