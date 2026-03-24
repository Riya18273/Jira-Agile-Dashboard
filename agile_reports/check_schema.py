import sqlite3
import pandas as pd

conn = sqlite3.connect('agile_database.db')
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
print("Tables:", tables['name'].tolist())

for table in tables['name']:
    cols = pd.read_sql(f"PRAGMA table_info('{table}')", conn)
    print(f"\nTable: {table}")
    print("Columns:", cols['name'].tolist())
conn.close()
