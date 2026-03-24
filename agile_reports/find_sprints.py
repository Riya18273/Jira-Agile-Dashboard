from jira_client import JiraClient
client = JiraClient()
# JQL to find ANY issue with a sprint
res = client.get("search/jql", params={"jql": 'sprint is not EMPTY', "fields": "project,sprint", "maxResults": 5})
if res.get('issues'):
    print("Issues with sprints found:")
    for issue in res['issues']:
        p = issue['fields']['project']['key']
        print(f"Key: {issue['key']} | Project: {p}")
else:
    print("No issues with sprints found in the WHOLE JIRA!")
