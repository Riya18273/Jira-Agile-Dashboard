import sqlite3
import pandas as pd
import os

class DatabaseManager:
    def __init__(self, db_name="agile_data.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Initialize the database connection."""
        conn = sqlite3.connect(self.db_name)
        conn.close()

    def _get_table_name(self, sheet_name):
        """Convert sheet names (e.g., 'Epic Summary') to table names (e.g., 'epic_summary')."""
        return sheet_name.lower().replace(" ", "_")

    def save_table(self, df, sheet_name, key_cols=None):
        """
        Save DataFrame to SQLite.
        If key_cols is provided, performs an upsert (merge) strategy.
        Otherwise, replaces the table.
        """
        if df is None or df.empty:
            print(f"DEBUG: No data to save for {sheet_name}")
            return

        table_name = self._get_table_name(sheet_name)
        conn = sqlite3.connect(self.db_name)
        
        try:
            print(f"DEBUG: Saving {len(df)} records to DB [{table_name}]", flush=True)
            
            if key_cols:
                # Upsert Logic:
                # 1. Check if table exists
                try:
                    existing_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                    
                    # Ensure merging columns match types if possible, though pandas handles mixed well usually
                    # 2. Concat and Drop Duplicates
                    #    We want new data to overwrite old data for the same key.
                    #    drop_duplicates(keep='last') does this if we append new data at the end.
                    combined_df = pd.concat([existing_df, df])
                    final_df = combined_df.drop_duplicates(subset=key_cols, keep='last')
                    
                    final_df.to_sql(table_name, conn, if_exists='replace', index=False)
                    print(f"DEBUG: Upsert complete. Total records: {len(final_df)}")
                    
                except Exception as e:
                    # Table might not exist or other error, fallback to create
                    # print(f"DEBUG: Table read failed ({e}), creating new.")
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
            else:
                # Full Replacement
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
        except Exception as e:
            print(f"ERROR: Failed to save table {table_name}: {e}")
        finally:
            conn.close()

    def read_table(self, sheet_name):
        """Read a table into a DataFrame."""
        table_name = self._get_table_name(sheet_name)
        if not os.path.exists(self.db_name):
            return pd.DataFrame() # File doesn't exist
            
        conn = sqlite3.connect(self.db_name)
        try:
            # Check if table exists
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                return pd.DataFrame()
                
            return pd.read_sql(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            print(f"ERROR: Failed to read table {table_name}: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def remove_deleted_records(self, sheet_name, key_col, current_keys):
        """Remove records that are no longer in the source."""
        table_name = self._get_table_name(sheet_name)
        conn = sqlite3.connect(self.db_name)
        try:
            existing_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            if existing_df.empty:
                return

            # Keep only records where key is in current_keys
            # Ensure key_col exists
            if key_col not in existing_df.columns:
                print(f"WARN: Key column {key_col} not found in {table_name}")
                return

            filtered_df = existing_df[existing_df[key_col].isin(current_keys)]
            
            # If we removed anything, save back
            if len(filtered_df) < len(existing_df):
                print(f"DEBUG: Removing {len(existing_df) - len(filtered_df)} deleted records from {table_name}")
                filtered_df.to_sql(table_name, conn, if_exists='replace', index=False)
                
        except Exception as e:
            print(f"ERROR: Failed to remove deleted records: {e}")
        finally:
            conn.close()
