from jira_client import JiraClient
client = JiraClient()
res = client.get("search/jql", params={"jql": 'key = "MFSD-9991"', "fields": "*all"})
if res.get('issues'):
    issue = res['issues'][0]
    fields = issue['fields']
    # Look for anything with 'sprint' or list of dicts with 'id', 'name', 'state'
    for k, v in fields.items():
        if v:
            if 'sprint' in k.lower() or 'customfield_10020' == k:
                print(f"FOUND {k}: {v}")
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'id' in v[0] and 'state' in v[0]:
                 print(f"POSSIBLE SPRINT {k}: {v}")
else:
    print("Issue not found")
