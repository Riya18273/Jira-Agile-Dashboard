import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()

class JiraClient:
    def __init__(self):
        self.url = (os.getenv("JIRA_URL") or os.getenv("JIRA_SERVER") or "").strip()
        self.email = (os.getenv("JIRA_EMAIL") or os.getenv("JIRA_USER") or "").strip()
        self.token = (os.getenv("JIRA_API_TOKEN") or "").strip()
        self.auth = HTTPBasicAuth(self.email, self.token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get(self, endpoint, params=None):
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Basic rate limit prevention
                if attempt == 0: time.sleep(0.1) 
                
                response = requests.get(
                    f"{self.url}/rest/api/3/{endpoint}",
                    auth=self.auth,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                # Handle Rate Limiting (429)
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 5 * (attempt + 1)))
                    print(f"WARNING: Rate limit hit for {endpoint}. Sleeping for {retry_after}s...", flush=True)
                    time.sleep(retry_after)
                    if attempt == max_retries - 1: raise
                    continue
                if e.response.status_code == 410 and endpoint == "search":
                    print("DEBUG: /search GONE. Retrying with /search/jql...", flush=True)
                    return self.get("search/jql", params=params)
                raise # Re-raise other HTTP errors (404, 500 etc)
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1: raise
                print(f"Retrying GET {endpoint} due to: {e}...", flush=True)
                time.sleep(2 * (attempt + 1))
        return {}

    def get_agile(self, endpoint, params=None):
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if attempt == 0: time.sleep(0.1)

                response = requests.get(
                    f"{self.url}/rest/agile/1.0/{endpoint}",
                    auth=self.auth,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 5 * (attempt + 1)))
                    print(f"WARNING: Agile Rate limit hit for {endpoint}. Sleeping for {retry_after}s...", flush=True)
                    time.sleep(retry_after)
                    if attempt == max_retries - 1: raise
                    continue
                raise
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1: raise
                print(f"Retrying Agile GET {endpoint} due to: {e}...", flush=True)
                time.sleep(2 * (attempt + 1))
        return {}

    def get_all_paginated(self, endpoint, api_type="classic", params=None):
        if params is None:
            params = {}
        
        # Atlassian is migrating /search to /search/jql in some instances
        # search/jql uses cursor-based pagination (nextPageToken/isLast)
        is_cursor_api = (endpoint == "search" or endpoint == "search/jql")
        if endpoint == "search":
            endpoint = "search/jql"
            
        results = []
        start_at = 0
        max_results = 50
        next_page_token = None
        
        while True:
            if is_cursor_api:
                if next_page_token:
                    params["nextPageToken"] = next_page_token
                # startAt is NOT used in search/jql cursor API
            else:
                params["startAt"] = start_at
                
            params["maxResults"] = max_results
            
            print(f"DEBUG: Fetching {endpoint} page (startAt={start_at}, nextToken={next_page_token})...", flush=True)
            
            if api_type == "agile":
                data = self.get_agile(endpoint, params=params)
            else:
                data = self.get(endpoint, params=params)
            
            if api_type == "agile":
                values = data.get("values", [])
                is_last = data.get("isLast", True)
            elif is_cursor_api:
                values = data.get("issues", [])
                is_last = data.get("isLast", True)
                next_page_token = data.get("nextPageToken")
            else:
                values = data.get("issues", [])
                total = data.get("total", 0)
                is_last = (start_at + len(values) >= total)
            
            print(f"DEBUG: Received {len(values)} items.", flush=True)
            results.extend(values)
            
            if is_last or not values:
                break
                
            if not is_cursor_api:
                start_at += len(values)
            
        return results
