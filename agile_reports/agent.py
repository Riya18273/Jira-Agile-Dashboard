import os
import json
from datetime import datetime, timedelta
from jira_client import JiraClient
from epic_summary import EpicSummaryExtractor
from sprint_summary import SprintSummaryExtractor
from release_summary import ReleaseSummaryExtractor
from issue_summary import IssueSummaryExtractor
from fix_version_summary import FixVersionSummaryExtractor
from worklog_summary import WorklogSummaryExtractor
from transition_history import TransitionHistoryExtractor
from backlog_summary import BacklogSummaryExtractor
from field_discovery import FieldDiscovery
from db_manager import DatabaseManager

STATE_FILE = "agent_state.json"

class JiraConnectorAgent:
    def __init__(self, project_key=None):
        self.client = JiraClient()
        suffix = f"_{project_key}" if project_key else ""
        self.db_name = f"agile_data{suffix}.db"
        self.state_file = f"agent_state{suffix}.json"
        
        self.db = DatabaseManager(self.db_name)
        self.state = self.load_state()
        
        # Discover fields once
        discovery = FieldDiscovery(self.client)
        self.agile_fields = discovery.discover_agile_fields()
        print(f"DEBUG: Using Agile fields: {self.agile_fields}")

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {"last_refresh": None}

    def save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f)

    def run(self, force_full=False, project_key=None):
        print(f"[{datetime.now()}] Starting refresh...", flush=True)
        if project_key:
            print(f"[{datetime.now()}] Filtering by Project: {project_key}", flush=True)
        
        last_refresh = self.state.get("last_refresh")
        if force_full or not last_refresh:
            updated_since = None
            print(f"[{datetime.now()}] Performing FULL extraction...", flush=True)
        else:
            dt = datetime.fromisoformat(last_refresh)
            updated_since = dt.strftime("%Y-%m-%d %H:%M")
            print(f"[{datetime.now()}] Performing INCREMENTAL extraction since {updated_since}...", flush=True)

        # 1. Epic Summary
        print(f"[{datetime.now()}] Extracting Epic Summary...", flush=True)
        epic_ext = EpicSummaryExtractor(self.client, sp_field=self.agile_fields['story_points'])
        epic_df = epic_ext.extract(updated_since=updated_since, project_key=project_key)
        print(f"[{datetime.now()}] Found {len(epic_df)} Epics. Saving to DB...", flush=True)
        self.db.save_table(epic_df, "Epic Summary", key_cols=["Epic Key"])

        # 2. Sprint Summary
        print(f"[{datetime.now()}] Extracting Sprint Summary...", flush=True)
        sprint_ext = SprintSummaryExtractor(self.client, 
                                           sprint_field=self.agile_fields['sprint'], 
                                           sp_field=self.agile_fields['story_points'])
        sprint_df = sprint_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(sprint_df)} Sprints. Saving to DB...", flush=True)
        self.db.save_table(sprint_df, "Sprint Summary", key_cols=["Sprint ID"])

        # 3. Release Summary
        print(f"[{datetime.now()}] Extracting Release Summary...", flush=True)
        release_ext = ReleaseSummaryExtractor(self.client)
        release_df = release_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(release_df)} Release entries. Saving to DB...", flush=True)
        self.db.save_table(release_df, "Release Summary")

        # 4. Issue Summary
        print(f"[{datetime.now()}] Extracting Issue Summary...", flush=True)
        issue_ext = IssueSummaryExtractor(self.client, 
                                          sprint_field=self.agile_fields['sprint'], 
                                          sp_field=self.agile_fields['story_points'])
        issue_df = issue_ext.extract(updated_since=updated_since, project_key=project_key)
        print(f"[{datetime.now()}] Found {len(issue_df)} Issues. Saving to DB...", flush=True)
        self.db.save_table(issue_df, "Issue Summary", key_cols=["Key"])

        # 5. Fix Version Summary
        print(f"[{datetime.now()}] Extracting Fix Version Summary...", flush=True)
        fv_ext = FixVersionSummaryExtractor(self.client)
        fv_df = fv_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(fv_df)} Fix Version mappings. Saving to DB...", flush=True)
        self.db.save_table(fv_df, "Fix Version Summary")

        # 6. Worklog Summary
        print(f"[{datetime.now()}] Extracting Worklog Summary...", flush=True)
        wl_ext = WorklogSummaryExtractor(self.client)
        wl_df = wl_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(wl_df)} Worklogs. Saving to DB...", flush=True)
        self.db.save_table(wl_df, "Worklog Summary", key_cols=["Worklog ID"])

        # 7. Transition History
        print(f"[{datetime.now()}] Extracting Transition History...", flush=True)
        th_ext = TransitionHistoryExtractor(self.client)
        th_df = th_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(th_df)} Transitions. Saving to DB...", flush=True)
        self.db.save_table(th_df, "Transition History")

        # 8. Backlog Health
        print(f"[{datetime.now()}] Extracting Backlog Health...", flush=True)
        bl_ext = BacklogSummaryExtractor(self.client, sp_field=self.agile_fields['story_points'])
        bl_df = bl_ext.extract(project_key=project_key)
        print(f"[{datetime.now()}] Found {len(bl_df)} Backlog items. Saving to DB...", flush=True)
        self.db.save_table(bl_df, "Backlog Health")

        # Handle Deletions
        if not issue_df.empty and "Key" in issue_df.columns:
            self.perform_deletion_cleanup(issue_df["Key"].tolist())
        else:
            print("Skipping deletion cleanup as no issues were fetched.")

        self.state["last_refresh"] = datetime.now().isoformat()
        self.save_state()
        print("Refresh completed successfully.")

    def perform_deletion_cleanup(self, current_issue_keys):
        print("Performing deletion cleanup...")
        self.db.remove_deleted_records("Issue Summary", "Key", current_issue_keys)
        # Add other sheets if needed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Jira Project Key to filter by")
    parser.add_argument("--force", action="store_true", help="Force full extraction")
    args = parser.parse_args()

    agent = JiraConnectorAgent(project_key=args.project)
    agent.run(force_full=args.force, project_key=args.project)
