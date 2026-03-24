
import sqlite3
import pandas as pd
import os

class AgileDatabaseManager:
    def __init__(self, db_path="agile_database.db"):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_dataframe(self, table_name, df):
        """Saves a dataframe to a specific table, replacing it entirely."""
        if df.empty:
            return
        
        # Convert list/dict columns to strings to avoid potential SQL errors if any
        df_clean = df.copy()
        for col in df_clean.columns:
            if df_clean[col].apply(lambda x: isinstance(x, (list, dict))).any():
                 df_clean[col] = df_clean[col].astype(str)
                 
        with self.get_connection() as conn:
            df_clean.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"Saved {len(df)} rows to table '{table_name}'")

    def load_table(self, table_name):
        """Loads an entire table as a Dataframe."""
        try:
            with self.get_connection() as conn:
                return pd.read_sql(f"SELECT * FROM '{table_name}'", conn)
        except Exception as e:
            print(f"Error loading table {table_name}: {e}")
            return pd.DataFrame() # Return empty if table doesn't exist

    def get_all_tables(self):
        """Returns a dictionary of all tables relevant to the dashboard."""
        tables = ["Sprint Summary", "Release Summary", "Epic Summary", "Issue Summary", "Worklog Summary"]
        data = {}
        for t in tables:
            data[t] = self.load_table(t)
        return data
