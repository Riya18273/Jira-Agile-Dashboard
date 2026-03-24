from jira_client import JiraClient
client = JiraClient()
res = client.get("search/jql", params={"jql": 'project = "MFSD"', "maxResults": 1, "fields": "key,summary"})
if res.get('issues'):
    issue = res['issues'][0]
    print(f"Content: {issue}")
else:
    print("No issues found")
