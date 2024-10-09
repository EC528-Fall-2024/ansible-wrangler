import requests 
from requests.auth import HTTPBasicAuth
import json

from llama_interface import generate_ansible_playbook

# Connect to ServiceNow API
# ServiceNow Instance Profile
instance = 'https://dev262513.service-now.com'
username = 'admin'
password = 'Gp8#xQ2b!'

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = 'Service Desk'  # desired user name to find the sys_id
url = instance + user_endpoint + "?sysparm_query=name=" + user_name

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Fetch user sys_id
response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

if response.status_code == 200:
    data = response.json()
    if len(data['result']) > 0:
        caller_sys_id = data['result'][0]['sys_id']
        print("Caller sys_id:", caller_sys_id)
    else:
        print("User not found")
        exit()
else:
    print(f"Error: {response.status_code}, {response.text}")
    exit()

# Updated filter query using the sys_id
filter_query = f"caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
url = instance + endpoint + "?sysparm_query=" + filter_query

# Fetch incident data
response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

if response.status_code == 200:
    data = response.json()
    
    # If no incidents are found
    if len(data['result']) == 0:
        print("No incidents found for the user.")
    
    # Output required fields for each incident



    for incident in data['result']:


        for root, _, files in os.walk(EXISTING_PLAYBOOKS_DIR):
            for file in files:
                if file.endswith(".yml") or file.endswith(".yaml"):
                    with open(os.path.join(root, file), 'r') as f:
                        playbook_content = f.read()
                        existing_playbooks.append(playbook_content)

        matched_playbook = evaluate_playbooks_with_llama(existing_playbooks, description)

        if matched_playbook == None:
            playbook = generate_ansible_playbook(incident.get("description"))
        else:
            playbook = matched_playbook
        output = {
            "short_description": incident.get("short_description"),
            "description": incident.get("description"),
            "number": incident.get("number"),
            "state": incident.get("state"),
            "suggested_playbook": playbook
        }
        
        print("Description: ", output["short_description"])
        print("Playbook: ", playbook)
else:
    print(f"Error: {response.status_code}, {response.text}")

