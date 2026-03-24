from jira_client import JiraClient
client = JiraClient()
# Get a sample issue from MFSD
res = client.get("search/jql", params={"jql": 'project = "MFSD"', "maxResults": 1})
if res.get('issues'):
    issue = res['issues'][0]
    print(f"Key: {issue['key']}")
    fields = issue['fields']
    print(f"Fields: {list(fields.keys())}")
    # Check for anything that looks like sprint or epic
    for k, v in fields.items():
        if v and ('sprint' in k.lower() or 'epic' in k.lower()):
            print(f"{k}: {v}")
else:
    print("No issues found in MFSD")
