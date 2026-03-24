import pandas as pd
from jira_client import JiraClient
from epic_summary import EpicSummaryExtractor
from sprint_summary import SprintSummaryExtractor
from release_summary import ReleaseSummaryExtractor
from issue_summary import IssueSummaryExtractor
from fix_version_summary import FixVersionSummaryExtractor
from worklog_summary import WorklogSummaryExtractor
from field_discovery import FieldDiscovery
import os

from dotenv import load_dotenv

def main():
    load_dotenv()
    client = JiraClient()
    # Support both naming conventions
    project_keys_str = os.getenv("JIRA_PROJECT_KEY") or os.getenv("PROJECT_KEY") 
    project_category = os.getenv("PROJECT_CATEGORY")

    project_keys = []
    
    if project_keys_str:
        project_keys = [k.strip() for k in project_keys_str.split(",")]
    elif project_category:
        print(f"Resolving projects for Category: '{project_category}'...", flush=True)
        # We need to fetch all projects in this category
        # Using a direct search on typical 'project' API is tedious, better to search issues or JQL to get keys?
        # Actually simplest is just to get all projects and filter.
        all_projects = client.get("project")
        if isinstance(all_projects, list):
            for p in all_projects:
                cat = p.get("projectCategory", {}).get("name")
                if cat == project_category:
                    project_keys.append(p["key"])
        print(f"Found {len(project_keys)} projects in category '{project_category}': {project_keys}", flush=True)

    if not project_keys and not project_category:
         # Default to empty list -> Global Extract
         project_keys = [None]
         
    output_file = "Agile_Master_Data.xlsx"
    print(f"Starting data extraction for: {project_keys if project_keys else 'ALL PROJECTS'}...", flush=True)

    # Dynamic Field Discovery
    discovery = FieldDiscovery(client)
    discovered = discovery.discover_agile_fields()
    sp_field = discovered.get('story_points')
    sprint_field = discovered.get('sprint')
    print(f"Agile Fields: Story Points={sp_field}, Sprint={sprint_field}")

    # Extraction Logic Update:
    # If we have a list of keys (from Category or manual), we need to handle it.
    # Most extractors in this codebase expect a single key OR None (for all).
    # To support multi-project efficiently without rewriting every extractor to take a list,
    # we can construct a JQL fragment: 'project in (A, B, C)'
    
    jql_filter = None
    if project_keys and project_keys[0] is not None:
        jql_filter = f'project in ({",".join(f"{k}" for k in project_keys)})'
    
    # We repurpose the 'project_key' argument in extractors to accept this Raw JQL if supported,
    # OR we modify extractors. Let's see if we can pass it as a special "key" or if we need to update extractors.
    # Looking at `issue_summary.py`: if project_key: jql += f'project = "{project_key}"'
    # This won't work with "project in (...)". 
    # WE MUST UPDATE EXTRACTORS TO ACCEPT `jql_filter` argument.
    
    # For now, let's keep the variable name `pkey` but pass the JQL string if it mimics the `project = ...` 
    # NO, we can't hack it easily because `f'project = "{pkey}"'` adds quotes.
    # We will assume we update extractors to check for `jql_filter` argument.
    
    pkey = None # We will use new jql_filter arg

    # Initialize DB Manager
    from agile_db_manager import AgileDatabaseManager
    db_manager = AgileDatabaseManager()

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # 1. Epic Summary
        print("Extracting Epic Summary...", flush=True)
        # Note: We need to update extractors to accept jql_filter
        epic_df = EpicSummaryExtractor(client, sp_field=sp_field).extract(project_key=pkey, jql_filter=jql_filter)
        epic_df.to_excel(writer, sheet_name="Epic Summary", index=False)
        db_manager.save_dataframe("Epic Summary", epic_df)

        # 2. Sprint Summary
        print("Extracting Sprint Summary...", flush=True)
        sprint_df = SprintSummaryExtractor(client, sp_field=sp_field, sprint_field=sprint_field).extract(project_key=pkey, jql_filter=jql_filter)
        sprint_df.to_excel(writer, sheet_name="Sprint Summary", index=False)
        db_manager.save_dataframe("Sprint Summary", sprint_df)

        # 3. Release Summary
        print("Extracting Release Summary...", flush=True)
        release_df = ReleaseSummaryExtractor(client, sp_field=sp_field).extract(project_key=pkey, jql_filter=jql_filter)
        release_df.to_excel(writer, sheet_name="Release Summary", index=False)
        db_manager.save_dataframe("Release Summary", release_df)

        # 4. Issue Summary
        print("Extracting Issue Summary...", flush=True)
        issue_df = IssueSummaryExtractor(client, sp_field=sp_field, sprint_field=sprint_field).extract(project_key=pkey, jql_filter=jql_filter)
        issue_df.to_excel(writer, sheet_name="Issue Summary", index=False)
        db_manager.save_dataframe("Issue Summary", issue_df)

        # 5. Worklog Summary
        print("Extracting Worklog Summary...", flush=True)
        worklog_df = WorklogSummaryExtractor(client).extract(project_key=pkey, jql_filter=jql_filter)
        worklog_df.to_excel(writer, sheet_name="Worklog Summary", index=False)
        db_manager.save_dataframe("Worklog Summary", worklog_df)

    print(f"Data extraction complete. Results saved to {output_file} and agile_database.db", flush=True)

if __name__ == "__main__":
    main()
