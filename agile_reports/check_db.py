import sqlite3
import pandas as pd

conn = sqlite3.connect("agile_database.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in agile_database.db:")
for t in tables:
    print(f"- {t[0]}")
    try:
        count = pd.read_sql(f"SELECT COUNT(*) as count FROM \"{t[0]}\"", conn).iloc[0]['count']
        print(f"  Rows: {count}")
    except Exception as e:
        print(f"  Error count: {e}")
conn.close()
