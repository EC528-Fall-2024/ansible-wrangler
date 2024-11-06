import requests 
from requests.auth import HTTPBasicAuth
import json
import os
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama, create_faiss_index
from git_interface import upload_new_playbook_to_repo

# Connect to ServiceNow API
# ServiceNow Instance Profile
instance = 'https://dev248794.service-now.com'
username = 'admin'
password = '$1sh2t+VcALL'

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

github_token = ""  # Replace with your actual GitHub token
file_path = "existing_playbooks/my_new_playbook.yaml"  # Specify the file path in the repo

REPO_OWNER = "EC528-Fall-2024"  # Your GitHub organization or username
REPO_NAME = "ansible-wrangler"  # Your repository name
BRANCH_NAME = "main"  # The branch where you want to add the playbook
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Form the complete URL with filters and ordering by number in ascending order
user_name = 'Service Desk'  # desired user name to find the sys_id
incident_number = 'INC0010007'  # desired incident number to find the playbook for
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

outputs =[]


if response.status_code == 200:

    create_faiss_index()

    data = response.json()
    
    # If no incidents are found
    if len(data['result']) == 0:
        print("No incidents found for the user.")
    
    # Output required fields for each incident


    #print(data['result'])
    for incident in data['result']:
        if(incident.get("number") == incident_number):
        

            playbook = generate_ansible_playbook(incident.get("short_description"))
            
            output = {
                "short_description": incident.get("short_description"),
                "description": incident.get("description"),
                "number": incident.get("number"),
                "state": incident.get("state"),
                "suggested_playbook": playbook
            }
            print("\n\nIncident details:")
            print("User: ", user_name)
            print("Description: ", output["short_description"])
            print("Incident Number: ", output["number"])
            print("\n\nSuggested playbook:")
            print("Playbook: ", playbook)

else:
    print(f"Error: {response.status_code}, {response.text}")

if github_token != "":
    i=10
    for output in outputs:
        upload_new_playbook_to_repo(BRANCH_NAME, file_path.split('.')[0]+str(i)+'.yaml', output["suggested_playbook"], GITHUB_API_URL, github_token)
        i+=1
