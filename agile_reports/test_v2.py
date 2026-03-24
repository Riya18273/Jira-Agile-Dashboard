import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()
server = os.getenv("JIRA_SERVER")
user = os.getenv("JIRA_USER")
token = os.getenv("JIRA_API_TOKEN")

auth = HTTPBasicAuth(user, token)
jql = 'project in ("PDB","MEG","MFS5T","M5R","PDLR")'
response = requests.get(
    f"{server}/rest/api/2/search",
    auth=auth,
    params={"jql": jql, "maxResults": 0}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Total: {response.json().get('total')}")
else:
    print(f"Error: {response.text}")
