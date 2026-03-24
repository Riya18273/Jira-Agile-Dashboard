from jira_client import JiraClient
client = JiraClient()
# JQL to find Epics in MFSD or category MFS-SD
jql = 'issuetype = Epic AND category = "MFS-SD"'
res = client.get("search/jql", params={"jql": jql, "maxResults": 1})
print(f"Epics in MFS-SD category: {res.get('total')}") # Wait, total is missing.
issues = res.get('issues', [])
print(f"Epics found: {len(issues)}")
if issues:
    print(f"Sample Epic: {issues[0]['key']}")
