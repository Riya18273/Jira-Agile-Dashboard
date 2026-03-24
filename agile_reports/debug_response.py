from jira_client import JiraClient
client = JiraClient()
res = client.get("search/jql", params={"jql": 'project = "MFSD"', "maxResults": 1})
print(f"Keys in response: {list(res.keys())}")
if res.get('issues'):
    issue = res['issues'][0]
    print(f"Type of issue: {type(issue)}")
    print(f"Content: {str(issue)[:500]}")
