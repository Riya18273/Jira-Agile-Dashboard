import pandas as pd
import os
from openpyxl import load_workbook

class ExcelManager:
    def __init__(self, filename="jira_data_model.xlsx"):
        self.filename = filename

    def save_sheet(self, df, sheet_name, key_cols=None):
        if df is None or df.empty:
            print(f"DEBUG: No data to save for {sheet_name}")
            return

        print(f"DEBUG: Saving {len(df)} records to {self.filename} [{sheet_name}]", flush=True)
        if not os.path.exists(self.filename):
            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            return

        # Load existing and replace sheet
        try:
            with pd.ExcelWriter(self.filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                # If we have key columns, we merge. Otherwise, replace.
                # For this agent, we usually want to replace or incrementally update.
                # However, PowerBI likes consistent sheets.
                
                if key_cols:
                    try:
                        existing_df = pd.read_excel(self.filename, sheet_name=sheet_name)
                        # Merge: Update existing keys, append new ones
                        # Combine and drop duplicates keeping the latest (from df)
                        updated_df = pd.concat([existing_df, df]).drop_duplicates(subset=key_cols, keep='last')
                        updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    except:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as e:
            # Fallback to creating new if append fails
            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    def read_sheet(self, sheet_name):
        if not os.path.exists(self.filename):
            return None
        try:
            return pd.read_excel(self.filename, sheet_name=sheet_name)
        except:
            return None

    def remove_deleted_records(self, sheet_name, key_col, current_keys):
        if not os.path.exists(self.filename):
            return
        
        df = self.read_sheet(sheet_name)
        if df is not None:
            # Keep only records where key is in current_keys
            filtered_df = df[df[key_col].isin(current_keys)]
            self.save_sheet(filtered_df, sheet_name)
