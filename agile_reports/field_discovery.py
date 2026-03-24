from jira_client import JiraClient

class FieldDiscovery:
    def __init__(self, client: JiraClient):
        self.client = client
        self._fields = None

    def get_all_fields(self):
        if self._fields is None:
            print("DEBUG: Fetching Jira field metadata for auto-discovery...")
            self._fields = self.client.get("field")
        return self._fields

    def find_field_id(self, name_keywords, schema_type=None):
        fields = self.get_all_fields()
        for f in fields:
            name = f.get('name', '').lower()
            schema = f.get('schema', {})
            custom = f.get('custom')
            
            # Check if all keywords match the name
            if all(k.lower() in name for k in name_keywords):
                if schema_type:
                    if schema.get('custom') == schema_type or schema.get('type') == schema_type:
                        return f.get('id')
                else:
                    return f.get('id')
        return None

    def discover_agile_fields(self):
        # 1. Story Points
        # Common names: "Story Points", "Story Point Estimate"
        sp_id = self.find_field_id(["story", "point"], "number") 
        if not sp_id:
            sp_id = self.find_field_id(["story", "point"]) # Fallback to name only
        
        # 2. Sprint
        # Common custom field type for Sprint
        sprint_id = self.find_field_id(["sprint"], "com.pyxis.greenhopper.jira:gh-sprint")
        if not sprint_id:
             sprint_id = self.find_field_id(["sprint"])

        return {
            "story_points": sp_id or "customfield_10033", # Fallback to current known
            "sprint": sprint_id or "customfield_10020"    # Fallback to current known
        }

if __name__ == "__main__":
    client = JiraClient()
    discovery = FieldDiscovery(client)
    fields = discovery.discover_agile_fields()
    print(f"DISCOVERED FIELDS: {fields}")
