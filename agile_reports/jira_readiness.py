import os
import requests
import json
from jira import JIRA
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL')
PROJECT_KEY = os.getenv('PROJECT_KEY')

def connect_jira():
    options = {'server': JIRA_SERVER}
    try:
        jira = JIRA(options, basic_auth=(JIRA_USER, JIRA_API_TOKEN))
        return jira
    except Exception as e:
        print(f"Failed to connect to Jira: {e}")
        return None




def get_field_id(jira, field_name):
    """
    Fetches all fields from Jira and returns the ID for the given field name.
    """
    try:
        fields = jira.fields()
        for field in fields:
            if field['name'].lower() == field_name.lower():
                return field['id']
    except Exception as e:
        print(f"Error fetching fields: {e}")
    return None

def get_issue_sprint_name(issue, sprint_field_id):
    """
    Extracts the Sprint Name from the issue.
    Jira Cloud Sprint field often contains a list of strings representation of Sprint objects.
    We prioritize Open/Active sprints, then Future.
    """
    if not sprint_field_id:
        return "Unknown Sprint"
    
    sprints_data = getattr(issue.fields, sprint_field_id, [])
    if not sprints_data:
        return "No Sprint Assigned"

    # sprints_data might be a list of dicts (if processed) or strings (raw API).
    # Python JIRA lib usually returns objects or strings depending on version/config.
    # We'll try to handle both string parsing and object attribute.
    
    active_sprint_name = None
    future_sprint_name = None

    for sprint in sprints_data:
        # Check if it's a string 'com.atlassian...' or object
        sprint_str = str(sprint)
        
        # Parse state and name
        # Format often: "com.atlassian.greenhopper.service.sprint.Sprint@...[id=123,rapidViewId=...,state=ACTIVE,name=Sprint 1,...]"
        state = "UNKNOWN"
        name = "Unknown"
        
        if 'state=' in sprint_str:
            parts = sprint_str.split(',')
            for part in parts:
                if 'state=' in part:
                    state = part.split('=')[1].strip()
                if 'name=' in part:
                    name = part.split('=')[1].strip()
                    # Clean up trailing bracket if present
                    if ']' in name:
                        name = name.split(']')[0]
        else:
             # Try object attribute access if available
             state = getattr(sprint, 'state', 'UNKNOWN')
             name = getattr(sprint, 'name', 'Unknown')

        if state.upper() == 'ACTIVE' or state.upper() == 'OPEN':
            active_sprint_name = name
        elif state.upper() == 'FUTURE':
            future_sprint_name = name

    return active_sprint_name if active_sprint_name else (future_sprint_name if future_sprint_name else "Completed/Other Sprint")

def get_active_sprint_issues(jira, project_key):
    """
    Fetches issues from the open and future sprints of the specified project.
    """
    # Fetch issues in open OR future sprints. 
    jql_query = f'project = "{project_key}" AND sprint in (openSprints(), futureSprints()) ORDER BY rank ASC'
    try:
        # Need issuetype for new logic
        issues = jira.search_issues(jql_query, maxResults=100) 
        return issues
    except Exception as e:
        print(f"Error fetching issues: {e}")
        return []

def check_compliance(issue, story_points_field_id, sprint_field_id):
    """
    Evaluates the issue and returns a list of FAILED criteria names.
    """
    failed_criteria = []
    
    # Check Issue Type
    issue_type = issue.fields.issuetype.name if hasattr(issue.fields, 'issuetype') else ""
    is_story = issue_type.lower() == 'story'

    # 1. Story Points Added (Only for Stories)
    if is_story:
        story_points = getattr(issue.fields, story_points_field_id, None) if story_points_field_id else None
        if story_points is None:
            failed_criteria.append("Story Points Missing")

    # 2. Assignee Present (Applies to ALL Issue Types)
    if not issue.fields.assignee:
        failed_criteria.append("No Assignee")

    # 3. Parent / Epic Linked (Only for Stories)
    if is_story:
        has_parent = hasattr(issue.fields, 'parent') and issue.fields.parent
        # For now assume parent field covers it
        if not has_parent:
             failed_criteria.append("Parent / Epic Linked Missing")

    # 4. Acceptance Criteria Present (Only for Stories)
    if is_story:
        description = issue.fields.description or ""
        has_ac = "Acceptance Criteria" in description or "AC:" in description
        if not has_ac:
            failed_criteria.append("Acceptance Criteria Missing")

    # 5. Description Completeness (Only for Stories)
    if is_story:
        description = issue.fields.description or ""
        if len(description) <= 50:
            failed_criteria.append("Description Incomplete")
    
    # 6. No Late Additions (Skipping for now as per previous logic simulating green)
    # if late: failed_criteria.append("Late Addition")

    return failed_criteria

def generate_aggregated_report(sprint_data):
    """
    Generates the markdown output grouped by Sprint.
    sprint_data structure: {'Sprint Name': {'Criteria Name': [list of issue keys]}}
    """
    markdown_output = ""
    
    for sprint_name, criteria_map in sprint_data.items():
        markdown_output += f"**Sprint: {sprint_name}**\n\n"
        markdown_output += "| Compliance CheckPoint | Compliance Score | Issue keys |\n"
        markdown_output += "| --- | --- | --- |\n"
        
        # Define the order of rows we want to show
        all_criteria = [
            "Story Points Missing", 
            "No Assignee", 
            "Parent / Epic Linked Missing", 
            "Acceptance Criteria Missing", 
            "Description Incomplete"
        ]
        
        for criteria in all_criteria:
            failed_keys = criteria_map.get(criteria, [])
            count = len(failed_keys)
            
            # Logic: Show ONLY if missing (Red). Highlight with Bold.
            if count > 0:
                score = "🔴"
                keys_str = ", ".join(failed_keys)
                # Markdown Bold for emphasis
                markdown_output += f"| **{criteria}** | {score} | {keys_str} |\n"
            
            # If Green (count == 0), we skip it to "highlight" only the missing points.
        
        markdown_output += "\n---\n\n"
        
    return markdown_output

def post_to_teams(content, dry_run=False):
    if dry_run:
        import sys
        # Force UTF-8 for console output to handle emojis on Windows
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 or other environments might not support reconfigure
            pass
            
        print("\n[DRY RUN] Content that would be posted to Teams:\n")
        print(content)
        print("\n[DRY RUN] End of content.\n")
        return

    if not TEAMS_WEBHOOK_URL:
        print("No Teams Webhook URL provided. Skipping posting.")
        print("Output:\n", content)
        return

    # Use simple text payload for robustness with large markdown chunks
    simple_payload = {"text": content}
    
    try:
        response = requests.post(TEAMS_WEBHOOK_URL, json=simple_payload)
        response.raise_for_status()
        print("Successfully posted chunk to Teams.")
    except Exception as e:
        print(f"Failed to post to Teams: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Jira Readiness Scorer')
    parser.add_argument('--dry-run', action='store_true', help='Print output to console instead of posting to Teams')
    args = parser.parse_args()

    if not all([JIRA_SERVER, JIRA_USER, JIRA_API_TOKEN, PROJECT_KEY]):
        print("Missing required environment variables (JIRA_SERVER, JIRA_USER, JIRA_API_TOKEN, PROJECT_KEY).")
        return
        
    if not args.dry_run and not TEAMS_WEBHOOK_URL:
         print("Missing TEAMS_WEBHOOK_URL. Only printing to console.")

    jira = connect_jira()
    if not jira:
        print("Could not connect to Jira.")
        return

    print(f"Connected to Jira at {JIRA_SERVER}.")
    
    # Resolve Field IDs dynamically
    print("Resolving field IDs...")
    story_points_id = get_field_id(jira, 'Story Points')
    sprint_id = get_field_id(jira, 'Sprint') 
    
    if not story_points_id:
        print("Warning: Could not find field 'Story Points'. Scoring for points will fail.")

    print(f"Fetching issues for project {PROJECT_KEY}...")
    issues = get_active_sprint_issues(jira, PROJECT_KEY)
    
    if not issues:
        print("No issues found in active or future sprints.")
        return

    print(f"Found {len(issues)} issues. Aggregating data...")
    
    # Structure: {'Sprint 1': {'Criteria A': ['KEY-1', 'KEY-2'], ...}, ...}
    aggregated_data = {}

    for issue in issues:
        sprint_name = get_issue_sprint_name(issue, sprint_id)
        if sprint_name not in aggregated_data:
            aggregated_data[sprint_name] = {}
            
        failed_items = check_compliance(issue, story_points_id, sprint_id)
        
        for failure in failed_items:
            if failure not in aggregated_data[sprint_name]:
                aggregated_data[sprint_name][failure] = []
            aggregated_data[sprint_name][failure].append(issue.key)

    # Generate Report
    print("Generating report...")
    report = generate_aggregated_report(aggregated_data)
    
    # Post to Teams (Chunking might be needed if very large, but aggregated is usually smaller)
    # The aggregated table per sprint could still be large if many keys.
    # We will try posting normally. If it fails, we might need to split by Sprint.
    
    # Let's split by Sprint just in case
    sprint_blocks = report.split("\n---\n\n")
    # Buffer blocks
    buffer = ""
    for block in sprint_blocks:
        if not block.strip(): continue
        
        if len(buffer) + len(block) > 10000: # Teams limit roughly
            post_to_teams(buffer, args.dry_run)
            buffer = block + "\n---\n\n"
        else:
            buffer += block + "\n---\n\n"
            
    if buffer.strip():
        post_to_teams(buffer, args.dry_run)


if __name__ == "__main__":
    main()
