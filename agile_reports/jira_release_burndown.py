import os
import pandas as pd
from jira import JIRA
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

JIRA_SERVER = os.getenv('JIRA_SERVER').strip() if os.getenv('JIRA_SERVER') else None
JIRA_USER = os.getenv('JIRA_USER').strip() if os.getenv('JIRA_USER') else None
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN').strip() if os.getenv('JIRA_API_TOKEN') else None
PROJECT_KEY = os.getenv('PROJECT_KEY').strip() if os.getenv('PROJECT_KEY') else None

def connect_jira():
    options = {'server': JIRA_SERVER}
    try:
        jira = JIRA(options, basic_auth=(JIRA_USER, JIRA_API_TOKEN))
        return jira
    except Exception as e:
        print(f"Failed to connect to Jira: {e}")
        return None

def get_field_id(jira, field_name):
    try:
        fields = jira.fields()
        for field in fields:
            if field['name'].lower() == field_name.lower():
                return field['id']
    except Exception as e:
        print(f"Error fetching fields: {e}")
    return None

def get_versions(jira, project_key):
    try:
        versions = jira.project_versions(project_key)
        return versions
    except Exception as e:
        print(f"Error fetching versions: {e}")
        return []

def get_release_data(jira, project_key, version_name):
    # JQL: project = PROJECT AND fixVersion = "VERSION"
    jql_query = f'project = "{project_key}" AND fixVersion = "{version_name}"'
    print(f"Running JQL: {jql_query}")
    
    issues = []
    block_size = 100
    start_at = 0
    
    while True:
        fetched_issues = jira.search_issues(
            jql_query, 
            startAt=start_at, 
            maxResults=block_size, 
            expand='changelog'
        )
        if not fetched_issues:
            break
        issues.extend(fetched_issues)
        start_at += block_size
        if len(fetched_issues) < block_size:
            break
            
    point_fields = ['customfield_10033', 'customfield_10016', 'customfield_10311']
    
    data = []
    for issue in issues:
        key = issue.key
        summary = issue.fields.summary
        status = issue.fields.status.name
        created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')
        
        # Get story points - try all known fields
        points = 0
        for field in point_fields:
            val = getattr(issue.fields, field, None)
            if val is not None and isinstance(val, (int, float)):
                points = val
                break
            
        # Find resolution date from changelog or field
        resolution_date = None
        if issue.fields.resolutiondate:
            resolution_date = datetime.strptime(issue.fields.resolutiondate[:10], '%Y-%m-%d')
        else:
            # Check changelog for transition to "Done" or equivalent
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.field == 'status' and item.toString.lower() in ['done', 'resolved', 'closed', 'completed']:
                        resolution_date = datetime.strptime(history.created[:10], '%Y-%m-%d')
        
        data.append({
            'Key': key,
            'Summary': summary,
            'Status': status,
            'Story Points': points,
            'Created Date': created_date,
            'Resolution Date': resolution_date
        })
        
    return pd.DataFrame(data)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Jira Release Burndown Extractor')
    parser.add_argument('--version', type=str, help='Specific Fix Version to target')
    args = parser.parse_args()

    if not all([JIRA_SERVER, JIRA_USER, JIRA_API_TOKEN, PROJECT_KEY]):
        print("Missing required environment variables.")
        return

    jira = connect_jira()
    if not jira:
        return

    print(f"Connected to Jira. Fetching versions for project {PROJECT_KEY}...")
    versions = get_versions(jira, PROJECT_KEY)
    
    if not versions:
        print(f"No versions found for project {PROJECT_KEY}")
        return

    selected_version = None
    if args.version:
        selected_version = next((v for v in versions if v.name == args.version), None)
        if not selected_version:
            print(f"Version '{args.version}' not found.")
            return
    else:
        # Default to latest version with points if possible, otherwise just latest
        selected_version = versions[-1]
        print(f"\nNo version specified. Defaulting to latest: {selected_version.name}")

    print(f"\nProcessing version: {selected_version.name}")
    df = get_release_data(jira, PROJECT_KEY, selected_version.name)
    
    if df.empty:
        print(f"No issues found for version {selected_version.name}")
        return

    # Export to Excel
    output_file = 'release_burndown_data.xlsx'
    df.to_excel(output_file, index=False)
    print(f"\nData exported to {output_file}")
    
    # Generate a simple burndown projection for Power BI verification
    # We want a table with dates from Start to Finish
    if not df.empty:
        start_date = df['Created Date'].min()
        end_date = df['Resolution Date'].max() if df['Resolution Date'].notnull().any() else datetime.now()
        
        # If version has a release date, use it as end date
        if hasattr(selected_version, 'releaseDate'):
             v_release_date = datetime.strptime(selected_version.releaseDate, '%Y-%m-%d')
             end_date = max(end_date, v_release_date)

        date_range = pd.date_range(start=start_date, end=end_date)
        burndown_data = []
        
        total_points = df['Story Points'].sum()
        
        for date in date_range:
            # Issues completed ON or BEFORE this date
            completed_points = df[df['Resolution Date'] <= date]['Story Points'].sum()
            remaining_points = total_points - completed_points
            burndown_data.append({
                'Date': date,
                'Total Points': total_points,
                'Remaining Points': remaining_points
            })
            
        burndown_df = pd.DataFrame(burndown_data)
        burndown_df.to_excel('burndown_calculation.xlsx', index=False)
        print(f"Burndown calculation exported to burndown_calculation.xlsx")

if __name__ == "__main__":
    main()
