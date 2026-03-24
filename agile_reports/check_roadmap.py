from jira_client import JiraClient
client = JiraClient()
cat = "MFS-Roadmap"
all_projects = client.get("project")
p_keys = []
for p in all_projects:
    if p.get("projectCategory", {}).get("name") == cat:
        p_keys.append(p["key"])
print(f"Projects in category '{cat}': {p_keys}")
