import sqlite3
import pandas as pd

conn = sqlite3.connect("agile_database.db")
df = pd.read_sql("SELECT \"Sprint ID\", COUNT(*) as count FROM \"Issue Summary\" GROUP BY 1", conn)
print("Sprint ID distribution in Issue Summary:")
print(df)
conn.close()
