import pandas as pd
from jira_client import JiraClient

class FixVersionSummaryExtractor:
    def __init__(self, client: JiraClient):
        self.client = client

    def extract(self, project_key=None):
        jql = 'fixVersion is not EMPTY'
        if project_key:
            jql += f' AND project = "{project_key}"'
        fields = "key,fixVersions"
        issues = self.client.get_all_paginated("search", params={"jql": jql, "fields": fields})
        
        version_data = []
        for issue in issues:
            for fv in issue['fields'].get('fixVersions', []):
                version_data.append({
                    "Fix Version ID": fv['id'],
                    "Fix Version Name": fv['name'],
                    "Key": issue['key']
                })

        return pd.DataFrame(version_data)

if __name__ == "__main__":
    client = JiraClient()
    extractor = FixVersionSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
