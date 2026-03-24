import sqlite3
import pandas as pd

conn = sqlite3.connect('agile_database.db')
try:
    df = pd.read_sql("SELECT DISTINCT \"Project Name\", \"Project Key\" FROM \"Issue Summary\"", conn)
    print(df)
except Exception as e:
    print(f"Error: {e}")
conn.close()
