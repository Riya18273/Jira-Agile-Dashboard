from jira_client import JiraClient
client = JiraClient()
jql = 'project = "PDB"'
data = client.get("search/jql", params={"jql": jql, "maxResults": 1})
print(f"Keys: {list(data.keys())}")
print(f"Total: {data.get('total')}")
print(f"Status: OK" if data else "Status: FAIL")
