# -*- coding: utf-8 -*-
import sys
import io
import pandas as pd
import sqlite3
from jira_client import JiraClient

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_jira_count(client, jql):
    # Use pagination to count issues because search/jql doesn't return 'total'
    try:
        issues = client.get_all_paginated("search", params={"jql": jql, "fields": "key"})
        return len(issues)
    except Exception as e:
        print(f"   Error fetching count for JQL: {jql} -> {e}")
        return 0

def main():
    client = JiraClient()
    db_path = "agile_database.db"
    
    # Projects in Category MFS-Roadmap
    # PDB, MEG, MFS5T, M5R, PDLR
    project_keys = ['PDB', 'MEG', 'MFS5T', 'M5R', 'PDLR']
    # Use double quotes for project keys just in case
    category_jql = 'project in ({})'.format(','.join(f'"{k}"' for k in project_keys))
    
    print("="*80)
    print("AGILE REPORTING VERIFICATION (JIRA vs SQLite)")
    print("Category: MFS-Roadmap")
    print("="*80)

    # 1. TOTAL ISSUE COUNT
    print(f"\n[1] TOTAL ISSUE COUNT")
    jira_total = get_jira_count(client, category_jql)
    
    conn = sqlite3.connect(db_path)
    try:
        db_total = pd.read_sql("SELECT COUNT(*) as count FROM \"Issue Summary\"", conn).iloc[0]['count']
    except Exception as e:
        print(f"Error reading Issue Summary: {e}")
        db_total = 0
    
    status = "✅ MATCH" if abs(jira_total - db_total) < 10 else "❌ MISMATCH" # Allow slight diff
    print(f"   Jira: {jira_total:,} | DB: {db_total:,} | {status}")

    # 2. RELEASE-WISE ISSUE COUNT (Top 5)
    print(f"\n[2] RELEASE-WISE ISSUE COUNT (SAMPLE)")
    try:
        # Check if table exists
        db_rel = pd.read_sql("SELECT \"Fix Version\", \"Total Issues\" FROM \"Release Summary\" WHERE \"Fix Version\" IS NOT NULL ORDER BY \"Total Issues\" DESC LIMIT 5", conn)
        print("   Checking sample releases from DB against Jira:")
        for _, row in db_rel.iterrows():
            rel = row['Fix Version']
            db_count = row['Total Issues']
            # Sanitize release name for JQL: escape double quotes if any
            clean_rel = rel.replace('"', '\\"')
            jql = f'fixVersion = "{clean_rel}" AND {category_jql}'
            jira_count = get_jira_count(client, jql)
            status = "✅" if abs(jira_count - db_count) < 10 else "❌"
            print(f"   - {rel}: Jira={jira_count} | DB={db_count} {status}")
    except Exception as e:
        print(f"   Error in Release Summary section: {e}")

    # 3. SPRINT-WISE ISSUE COUNT (SAMPLE)
    print(f"\n[3] SPRINT-WISE ISSUE COUNT (SAMPLE)")
    try:
        db_sprint = pd.read_sql("SELECT \"Sprint Name\", \"Count of Total Issues\" FROM \"Sprint Summary\" WHERE \"Sprint Name\" IS NOT NULL ORDER BY \"Count of Total Issues\" DESC LIMIT 5", conn)
        for _, row in db_sprint.iterrows():
            sprint = row['Sprint Name']
            db_count = row['Count of Total Issues']
            clean_sprint = sprint.replace('"', '\\"')
            jql = f'sprint = "{clean_sprint}" AND {category_jql}'
            jira_count = get_jira_count(client, jql)
            status = "✅" if abs(jira_count - db_count) < 10 else "❌"
            print(f"   - {sprint}: Jira={jira_count} | DB={db_count} {status}")
    except Exception as e:
        print(f"   Error in Sprint Summary section: {e}")

    # 4. WORKLOG TABLE UNIQUE ISSUES
    print(f"\n[4] WORKLOG TABLE UNIQUE ISSUES")
    try:
        # Table column is "Key" from check_schema results
        db_wl_issues = pd.read_sql("SELECT COUNT(DISTINCT \"Key\") as count FROM \"Worklog Summary\"", conn).iloc[0]['count']
        jira_wl_issues = get_jira_count(client, f'worklogDate != null AND {category_jql}')
        status = "✅" if abs(jira_wl_issues - db_wl_issues) < 20 else "❌" # Larger tolerance for worklogs
        print(f"   Jira: {jira_wl_issues:,} | DB: {db_wl_issues:,} | {status}")
    except Exception as e:
        print(f"   Error in Worklog section: {e}")

    # 5. TOTAL TIME SPENT (Total Hours)
    print(f"\n[5] TOTAL TIME SPENT (HOURS)")
    try:
        db_hours = pd.read_sql("SELECT SUM(\"Sum of Time Entry Log Time\") as total FROM \"Worklog Summary\"", conn).iloc[0]['total']
        print(f"   Total hours logged in DB: {db_hours:,.1f} hrs")
        # Check a few authors
        author_sample = pd.read_sql("SELECT \"Time Entry User\", SUM(\"Sum of Time Entry Log Time\") as hrs FROM \"Worklog Summary\" GROUP BY 1 ORDER BY 2 DESC LIMIT 3", conn)
        print("   Top authors in DB:")
        for _, row in author_sample.iterrows():
            author = row['Time Entry User']
            db_hrs = row['hrs']
            print(f"   - {author}: {db_hrs:,.1f} hrs")
    except Exception as e:
        print(f"   Error in Time Spent section: {e}")

    conn.close()
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
