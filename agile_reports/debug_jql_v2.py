import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("JIRA_SERVER")
user = os.getenv("JIRA_USER")
token = os.getenv("JIRA_API_TOKEN")
auth = HTTPBasicAuth(user, token)

def test_jql(jql):
    print(f"Testing JQL: {jql}")
    res = requests.get(f"{url}/rest/api/2/search", auth=auth, params={"jql": jql, "maxResults": 1})
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Total: {res.json().get('total')}")
    else:
        print(f"Error: {res.text}")

test_jql('project = "MFSD"')
test_jql('project in ("DOL4","DOSD","INTL4","MFSD")')
