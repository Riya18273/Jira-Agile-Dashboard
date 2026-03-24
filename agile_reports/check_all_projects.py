import sqlite3
import pandas as pd

conn = sqlite3.connect('agile_database.db')
tables = ["Sprint Summary", "Epic Summary", "Issue Summary", "Release Summary", "Worklog Summary"]
for t in tables:
    try:
        df = pd.read_sql(f"SELECT DISTINCT \"Project Name\" FROM \"{t}\"", conn)
        print(f"Table {t} Projects: {df['Project Name'].unique()}")
    except Exception as e:
        print(f"Table {t} error: {e}")
conn.close()
