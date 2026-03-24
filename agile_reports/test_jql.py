from jira_client import JiraClient
client = JiraClient()
jql = 'project = "MFSD"'
res = client.get("search", params={"jql": jql, "maxResults": 1})
print(f"JQL: {jql}")
print(f"Total: {res.get('total')}")
if res.get('issues'):
    print(f"Sample: {res.get('issues')[0]['key']}")
else:
    print("No issues found")
