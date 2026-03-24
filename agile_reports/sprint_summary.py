import pandas as pd
from jira_client import JiraClient

class SprintSummaryExtractor:
    def __init__(self, client: JiraClient, sprint_field='customfield_10020', sp_field='customfield_10033'):
        self.client = client
        self.sprint_field = sprint_field
        self.sp_field = sp_field

    def get_boards(self):
        return self.client.get_all_paginated("board", api_type="agile")

    def get_sprints(self, board_id):
        return self.client.get_all_paginated(f"board/{board_id}/sprint", api_type="agile")

    def get_sprint_issues(self, board_id, sprint_id):
        fields = f"key,issuetype,status,{self.sp_field},fixVersions,project"
        return self.client.get_all_paginated(f"board/{board_id}/sprint/{sprint_id}/issue", api_type="agile", params={"fields": fields})

    def extract(self, project_key=None, jql_filter=None):
        if not project_key and not jql_filter:
            print("ERROR: Project Key or JQL Filter is required for efficient Sprint extraction.")
            return pd.DataFrame()

        board_name_map = {}
        board_project_map = {} # board_id -> {name, key}
        
        print("DEBUG: Fetching boards for project mapping...", flush=True)
        try:
            # We fetch all boards to be sure we can map any sprint we find
            all_boards = self.client.get_all_paginated("board", api_type="agile")
            for b in all_boards:
                b_id = b['id']
                board_name_map[b_id] = b['name']
                loc = b.get('location', {})
                if loc.get('projectKey'):
                    board_project_map[b_id] = {
                        "name": loc.get('projectName'),
                        "key": loc.get('projectKey')
                    }
        except Exception as e:
            print(f"Warning: Could not fetch boards: {e}")

        print(f"DEBUG: Efficiently fetching all issues with sprints for {project_key or 'JQL Filter'}...", flush=True)
        # JQL for issues with ANY sprint data
        sprint_jql = 'sprint is not EMPTY'
        
        if jql_filter:
            sprint_jql = f'({jql_filter}) AND {sprint_jql}'
        elif project_key:
            sprint_jql = f'project = "{project_key}" AND {sprint_jql}'
        fields = f"key,status,issuetype,sprint,{self.sprint_field},{self.sp_field},fixVersions,project"
        
        issues = self.client.get_all_paginated("search", params={"jql": sprint_jql, "fields": fields})
        print(f"DEBUG: Scanned {len(issues)} issues for sprint data.", flush=True)
        
        sprint_data_map = {} # sprint_id -> {metadata, issues, aggregated_stats}

        for issue in issues:
            f = issue.get('fields', {})
            # Check both possible sprint fields
            sprints = f.get(self.sprint_field) or f.get('sprint') or []
            if not sprints: continue
            
            # If it's a single dict, make it a list
            if isinstance(sprints, dict):
                sprints = [sprints]
            
            for s in sprints:
                if not isinstance(s, dict): continue
                s_id = s.get('id')
                if not s_id: continue
                
                if s_id not in sprint_data_map:
                    board_id = s.get('boardId')
                    sprint_data_map[s_id] = {
                        "name": s.get('name'),
                        "state": s.get('state'),
                        "boardId": board_id,
                        "boardName": board_name_map.get(board_id, f"Board {board_id}"),
                        "goal": s.get('goal'),
                        "startDate": s.get('startDate'),
                        "endDate": s.get('endDate'),
                        "completeDate": s.get('completeDate'),
                        "issues": [],
                        "total_issues": 0,
                        "completed_issues": 0,
                        "total_sp": 0.0,
                        "completed_sp": 0.0,
                        "total_defects": 0,
                        "open_defects": 0,
                        "fix_versions": set()
                    }
                
                sprint_entry = sprint_data_map[s_id]
                sprint_entry["issues"].append(issue)
                sprint_entry["total_issues"] += 1

                is_done = f['status']['statusCategory']['key'] == 'done'
                sp = float(f.get(self.sp_field) or 0)
                
                sprint_entry["total_sp"] += sp
                if is_done:
                    sprint_entry["completed_issues"] += 1
                    sprint_entry["completed_sp"] += sp
                
                if f['issuetype']['name'].lower() in ['bug', 'defect']:
                    sprint_entry["total_defects"] += 1
                    if not is_done:
                        sprint_entry["open_defects"] += 1
                
                for fv in f.get('fixVersions', []):
                    sprint_entry["fix_versions"].add(fv['name'])

        sprint_data = []
        for s_id, s_entry in sprint_data_map.items():
            # 1. Try mapping via Board ID
            b_id = s_entry.get('boardId')
            proj_info = board_project_map.get(b_id)
            
            p_name = "Unknown"
            if proj_info:
                p_name = proj_info.get("name")
            else:
                # 2. Fallback: Dynamically determine project name from the first issue in the sprint
                if s_entry["issues"]:
                    try:
                         p_name = s_entry["issues"][0]['fields']['project']['name']
                    except:
                        pass
            
            if project_key:
                 # If we were called for a specific project, ensure we report that if inference failed
                 if p_name == "Unknown": p_name = project_key

            sprint_data.append({
                "Board ID": b_id,
                "Board Name": s_entry.get('boardName'),
                "Sprint ID": s_id,
                "Sprint Name": s_entry.get('name'),
                "Project Name": p_name,
                "State": s_entry.get('state'),
                "Start Date": s_entry.get('startDate'),
                "End Date": s_entry.get('endDate'),
                "Complete Date": s_entry.get('completeDate'),
                "Goal": s_entry.get('goal'),
                "Fix Versions": ",".join(s_entry["fix_versions"]),
                "Count of Total Issues": s_entry["total_issues"],
                "Count of Completed Issues": s_entry["completed_issues"],
                "Total of Committed Story Points": s_entry["total_sp"],
                "Total of Completed Story Points": s_entry["completed_sp"],
                "Total of Remaining Story Points": s_entry["total_sp"] - s_entry["completed_sp"],
                "Total Count of Defect": s_entry["total_defects"],
                "Total of Count of Open Defect": s_entry["open_defects"],
                "Total of Count of Completed Defect": s_entry["total_defects"] - s_entry["open_defects"]
            })

        return pd.DataFrame(sprint_data)

if __name__ == "__main__":
    client = JiraClient()
    extractor = SprintSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
