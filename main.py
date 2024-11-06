import requests
from requests.auth import HTTPBasicAuth
import json
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama

# Connect to ServiceNow API
# ServiceNow Instance Profile
instance = 'https://dev248794.service-now.com'
username = 'admin'
password = '$1sh2t+VcALL'

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = 'System Administrator'  # desired user name to find the sys_id
incident_number = 'INC0010013'  # desired incident number to find the playbook for
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
        if incident.get("number") == incident_number:
            description = incident.get("description")
            short_description = incident.get("short_description")

            # Define GitHub repository details
            git_repo_url = 'https://github.com/EC528-Fall-2024/ansible-wrangler.git' ## GITHUB URL
            branch = 'Mac-New' ## BRANCH
            directory = 'existing_playbooks' ## DIRECTORY

            # Evaluate existing playbooks from GitHub
            matched_playbook = evaluate_playbooks_with_llama(
                git_repo_url,
                branch,
                directory,
                short_description
            )

            if matched_playbook is None:
                # Generate a new playbook if no match is found
                playbook = generate_ansible_playbook(description)
            else:
                playbook = matched_playbook

            output = {
                "short_description": short_description,
                "description": description,
                "number": incident.get("number"),
                "state": incident.get("state"),
                "suggested_playbook": playbook
            }
            print("\n\nIncident details:")
            print("User: ", user_name)
            print("Description: ", output["short_description"])
            print("Incident Number: ", output["number"])
            print("\n\nSuggested playbook:")
            print("Playbook:\n", playbook)
else:
    print(f"Error: {response.status_code}, {response.text}")
