
import sqlite3
import pandas as pd
from jira_client import JiraClient
import os
from dotenv import load_dotenv
import sys
import requests

# Set encoding to utf-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def get_jira_count(client, jql):
    # Using the search/jql endpoint structure discovered previously
    # Since we only need the total, we can use maxResults=1
    try:
        url = f"{client.url}/rest/api/3/search/jql"
        params = {"jql": jql, "maxResults": 1}
        resp = requests.get(url, auth=client.auth, headers=client.headers, params=params)
        if resp.status_code == 200:
            # Note: search/jql doesn't return 'total' in some versions, 
            # but we can check if 'issues' exists. 
            # Actually, let's try the classic /search first for total.
            classic_url = f"{client.url}/rest/api/3/search"
            c_resp = requests.get(classic_url, auth=client.auth, headers=client.headers, params={"jql": jql, "maxResults": 0})
            if c_resp.status_code == 200:
                return c_resp.json().get("total", 0)
    except:
        pass
    return 0

def reconcile_agile():
    load_dotenv()
    client = JiraClient()
    conn = sqlite3.connect("agile_database.db")
    
    projects = ['PDB', 'MEG', 'MFS5T', 'M5R']
    metrics = ["Epics", "Releases", "Sprints", "Defects"]
    
    print(f"{'Project':<10} | {'Metric':<10} | {'Jira API':<10} | {'Dashboard':<10} | {'Status'}")
    print("-" * 65)

    # Pre-load boards for sprint counting
    all_boards = client.get_all_paginated("board", api_type="agile")

    for p in projects:
        # --- 1. EPICS ---
        jira_epics = get_jira_count(client, f'project = "{p}" AND issuetype = Epic')
        db_epics = pd.read_sql(f"SELECT COUNT(*) FROM 'Epic Summary' WHERE `Project Key` = '{p}'", conn).iloc[0,0]
        print(f"{p:<10} | Epics      | {jira_epics:<10} | {db_epics:<10} | {'OK' if jira_epics == db_epics else 'DIFF'}")

        # --- 2. RELEASES (Versions) ---
        versions = client.get(f"project/{p}/versions")
        jira_rels = len(versions) if isinstance(versions, list) else 0
        db_rels = pd.read_sql(f"SELECT COUNT(*) FROM 'Release Summary' WHERE `Project Key` = '{p}'", conn).iloc[0,0]
        print(f"{'':<10} | Releases   | {jira_rels:<10} | {db_rels:<10} | {'OK' if jira_rels == db_rels else 'DIFF'}")

        # --- 3. SPRINTS ---
        # Find boards for project, then count sprints
        p_boards = [b['id'] for b in all_boards if b.get('location', {}).get('projectKey') == p]
        jira_sprints = 0
        for b_id in p_boards:
            try:
                sprints = client.get_all_paginated(f"board/{b_id}/sprint", api_type="agile")
                jira_sprints += len(sprints)
            except: pass
        # Database counts sprints by project name usually in Sprint Summary, let's try to map
        # We'll use the counts we saved
        db_sprints = pd.read_sql(f"SELECT COUNT(*) FROM 'Sprint Summary' WHERE `Project Name` LIKE '%{p}%' OR `Board Name` LIKE '%{p}%'", conn).iloc[0,0]
        # Better DB query for sprints if we have project key? Sprint summary doesn't have key.
        # Let's check how many sprints in DB are associated with issues from this project.
        print(f"{'':<10} | Sprints    | {jira_sprints:<10} | {db_sprints:<10} | {'OK' if jira_sprints == db_sprints else 'CHECK'}")

        # --- 4. DEFECTS ---
        jira_defects = get_jira_count(client, f'project = "{p}" AND issuetype in (Defect, Bug)')
        db_defects = pd.read_sql(f"SELECT COUNT(*) FROM 'Issue Summary' WHERE `Project Key` = '{p}' AND `Issue Type` IN ('Defect', 'Bug')", conn).iloc[0,0]
        print(f"{'':<10} | Defects    | {jira_defects:<10} | {db_defects:<10} | {'OK' if jira_defects == db_defects else 'DIFF'}")
        print("-" * 65)

    conn.close()

if __name__ == "__main__":
    reconcile_agile()
