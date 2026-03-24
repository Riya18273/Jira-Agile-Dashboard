from jira_client import JiraClient
client = JiraClient()
jql = 'project = "PDB"'
data = client.get("search/jql", params={"jql": jql, "maxResults": 1})
print(f"Keys: {list(data.keys())}")
# Check if total is anywhere
for k, v in data.items():
    if k.lower() == 'total':
        print(f"Found total: {v}")
