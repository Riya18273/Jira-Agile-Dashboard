from jira_client import JiraClient
client = JiraClient()
for p in ['DOL4', 'DOSD', 'INTL4']:
    res = client.get("search/jql", params={"jql": f'project = "{p}"', "fields": "*all", "maxResults": 1})
    if res.get('issues'):
        issue = res['issues'][0]
        print(f"Project {p}: Key {issue['key']}")
        fields = issue['fields']
        for k, v in fields.items():
            if v and ('sprint' in k.lower() or 'epic' in k.lower()):
                 print(f"  {k}: {v}")
    else:
        print(f"Project {p}: No issues found")
