from jira_client import JiraClient
client = JiraClient()
projects = ['PDB', 'MEG', 'MFS5T', 'M5R', 'PDLR']
jql = 'project in ({}) AND sprint is not EMPTY'.format(','.join(f'"{k}"' for k in projects))
res = client.get("search/jql", params={"jql": jql, "maxResults": 1})
print(f"Issues with Sprints in MFS-Roadmap: {len(res.get('issues', []))}")
