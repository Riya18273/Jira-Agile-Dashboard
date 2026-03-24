import pandas as pd
from jira_client import JiraClient

class EpicSummaryExtractor:
    def __init__(self, client: JiraClient, sp_field='customfield_10033'):
        self.client = client
        self.sp_field = sp_field

    def get_epics(self, updated_since=None, project_key=None):
        jql = 'issuetype = Epic'
        if project_key:
            jql += f' AND project = "{project_key}"'
        if updated_since:
            jql += f' AND updated >= "{updated_since}"'
        return self.client.get_all_paginated("search", params={"jql": jql, "fields": "key,summary,status"})

    def get_epic_children(self, epic_key, updated_since=None):
        jql = f'"Epic Link" = {epic_key} OR parent = {epic_key}'
        fields = "key,issuetype,status,customfield_10033" 
        return self.client.get_all_paginated("search", params={"jql": jql, "fields": fields})

    def extract(self, updated_since=None, project_key=None, jql_filter=None):
        # 1. Fetch Epics
        jql = 'issuetype = Epic'
        if jql_filter:
            jql += f' AND {jql_filter}'
        elif project_key:
            jql += f' AND project = "{project_key}"'
        
        if updated_since:
            jql += f' AND updated >= "{updated_since}"'
            
        # Request project field
        epics = self.client.get_all_paginated("search", params={"jql": jql, "fields": "key,summary,status,project"})
        
        epic_data = []
        total_epics = len(epics)
        if not epics:
            return pd.DataFrame()

        child_jql = '("Epic Link" is not EMPTY OR parent is not EMPTY)'
        if jql_filter:
            child_jql = f'({jql_filter}) AND {child_jql}'
        elif project_key:
            child_jql = f'project = "{project_key}" AND {child_jql}'
        child_fields = f"key,issuetype,status,customfield_10014,parent,{self.sp_field}"
        all_children = self.client.get_all_paginated("search", params={"jql": child_jql, "fields": child_fields})
        
        # Group children by Epic Key
        # customfield_10014 is the standard 'Epic Link' field
        children_by_epic = {}
        for child in all_children:
            f = child.get('fields', {})
            epic_link = f.get('customfield_10014')
            parent_key = (f.get('parent') or {}).get('key')
            
            target_epic = epic_link or parent_key
            if target_epic:
                if target_epic not in children_by_epic:
                    children_by_epic[target_epic] = []
                children_by_epic[target_epic].append(child)

        print(f"DEBUG: Grouped {len(all_children)} children into {len(children_by_epic)} epics.", flush=True)

        for i, epic in enumerate(epics):
            key = epic['key']
            fields = epic.get('fields', {})
            summary = fields.get('summary', 'No Summary')
            status = (fields.get('status') or {}).get('name')
            project = fields.get('project') or {}
            p_key = project.get('key')
            p_name = project.get('name')
            
            # Use cached children for the current epic
            children = children_by_epic.get(key, [])
            
            # ... process children ...

            # Group children by type
            stories = [c for c in children if (c.get('fields') or {}).get('issuetype', {}).get('name') == 'Story']
            non_stories = [c for c in children if (c.get('fields') or {}).get('issuetype', {}).get('name') not in ['Story', 'Sub-task', 'Epic']]
            
            total_stories = len(stories)
            open_stories = len([s for s in stories if (s.get('fields', {}).get('status') or {}).get('statusCategory', {}).get('key') != 'done'])
            completed_stories = total_stories - open_stories
            
            sp_field = self.sp_field
            total_sp = sum([float((s.get('fields') or {}).get(sp_field) or 0) for s in stories])
            completed_sp = sum([float((s.get('fields') or {}).get(sp_field) or 0) for s in stories if (s.get('fields', {}).get('status') or {}).get('statusCategory', {}).get('key') == 'done'])
            remaining_sp = total_sp - completed_sp
            
            completion_pct = (completed_sp / total_sp * 100) if total_sp > 0 else (100 if total_stories > 0 and open_stories == 0 else 0)
            stories_no_sp = len([s for s in stories if (s.get('fields') or {}).get(sp_field) is None])
            
            cnt_non_stories = len(non_stories)
            cnt_completed_non_stories = len([n for n in non_stories if (n.get('fields', {}).get('status') or {}).get('statusCategory', {}).get('key') == 'done'])
            cnt_open_non_stories = cnt_non_stories - cnt_completed_non_stories
            
            # Defects associated with Stories (either as sub-tasks or linked issues)
            # For simplicity, we assume "associated" means sub-tasks of stories here, 
            # as bulk fetching linked issues is much more expensive.
            total_defects = 0
            for s in stories:
                s_key = s['key']
                # Check if the story itself has sub-tasks that are defects
                sub_tasks_of_story = children_by_epic.get(s_key, []) # children_by_epic might contain sub-tasks if they are linked to the story's key
                s_defects = [st for st in sub_tasks_of_story if (st.get('fields', {}).get('issuetype', {}).get('name') or '').lower() in ['bug', 'defect']]
                total_defects += len(s_defects)

            epic_data.append({
                "Epic Key": key,
                "Project Key": p_key,
                "Project Name": p_name,
                "Epic Summary": summary,
                "Epic Status": status,
                "Total Stories Count": total_stories,
                "Open Stories Count": open_stories,
                "Completed Stories Count": completed_stories,
                "Completed Story Points": completed_sp,
                "Remaining Story Points": remaining_sp,
                "% Completion": f"{completion_pct:.2f}%",
                "Stories Counts without story points": stories_no_sp,
                "Count of Non-stories Issues linked": cnt_non_stories,
                "Count of Completed Non-stories Issues linked": cnt_completed_non_stories,
                "Count of Open Non-stories Issues linked": cnt_open_non_stories,
                "Count of Total Defects": total_defects
            })

        return pd.DataFrame(epic_data)

if __name__ == "__main__":
    client = JiraClient()
    extractor = EpicSummaryExtractor(client)
    df = extractor.extract()
    print(df.head())
