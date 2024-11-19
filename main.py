import requests
from requests.auth import HTTPBasicAuth
import json
import os
import time
import subprocess
from dotenv import load_dotenv
from llama_interface import generate_ansible_playbook, create_faiss_index
from awx import create_job_template, launch_job, track_job, trigger_project_update
from utils import check_gpu_availability
# Load environment variables
load_dotenv(override=True)
use_gpu=check_gpu_availability()
# Connect to ServiceNow API
instance = os.getenv("INSTANCE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
journal_endpoint = '/api/now/table/sys_journal_field'
endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = "System Administrator" ## UPDATE USER
url = instance + user_endpoint + "?sysparm_query=name=" + user_name

# Define GitHub repository details
git_repo_url = os.getenv("GITHUB_URL")
branch = os.getenv("BRANCH")
existing_directory = os.getenv("EXISTING_DIRECTORY")
out_directory = os.getenv("OUT_DIRECTORY")

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Fetch user sys_id
create_faiss_index(use_gpu=use_gpu)


def process_playbook(description, incident_number, use_gpu):

    playbook = generate_ansible_playbook(description, use_gpu=use_gpu)  # Assumes generate_ansible_playbook is available
    
    return playbook

def update_incident(url, payload, headers, username, password):
    response = requests.patch(url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
    if response.status_code != 200: 
        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
    return

def awx(incident_number, playbook):
    playbook_filename = f"playbook_{incident_number}.yml"
    repo_path = os.path.abspath('.')
    saved_directory = os.path.join(repo_path, out_directory)
    os.makedirs(saved_directory, exist_ok=True)
    playbook_path = os.path.join(saved_directory, playbook_filename)
    with open(playbook_path, 'w') as f:
        f.write(playbook)
    # Commit and push the accepted playbook to Git
    subprocess.run(['git', 'add', playbook_path], cwd=repo_path)
    print(playbook_path)
    
    subprocess.run(['git', 'commit', '-m', f'Add playbook for incident {incident_number}'], cwd=repo_path)
    subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path)
    # Trigger project update in AWX to sync the latest playbooks
    project_id = int(os.getenv("PROJECT_ID"))
    trigger_project_update(project_id)
    # Set playbook path for AWX
    awx_playbook_path = f"{out_directory}/{playbook_filename}"
    # Use AWX to run the playbook
    job_template_id = create_job_template(awx_playbook_path)
    job_id = launch_job(job_template_id)
    job_status = track_job(job_id)
    return job_status

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
# Fetch incident data
while True:
    filter_query = f"caller_id={caller_sys_id}^active=true^universal_requestISEMPTY&sysparm_fields=number,short_description,state,description,sys_id"
    url = instance + endpoint + "?sysparm_query=" + filter_query
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

    if response.status_code == 200:
        
        data = response.json()
        # If no incidents are found
        if len(data['result']) == 0:
            print("No incidents found for the user.")
            continue
        
        # Output required fields for each incident
        for incident in data['result']:
            incident_number = incident.get("number")
            incident_state = incident.get("state")
            incident_sys_id = incident.get("sys_id")
            # Check if incident is already processed
            if incident_state in ["3","4","5","6"] :
                continue
            else:
                description = incident.get("description")
                short_description = incident.get("short_description")
                if incident_state == "1":
                    update_url = instance + endpoint + '/' + incident_sys_id
                    payload = {
                        'state' : 2,
                        'comments': 'Hello,\n\nWe have received your incident and are currently in the process of generating the playbook. Once it\'s ready, you will be able to review it and decide whether it works for your needs.\n\nIf you are satisfied with the generated playbook, please change the incident state to Resolved.\nIf the playbook does not meet your needs, simply write the comment "Regenerate", and I will regenerate the playbook for you.\n\nThank you for your patience!'
                    }
                    response = requests.patch(update_url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
                    if response.status_code != 200: 
                        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
                    playbook = process_playbook(description, incident_number,use_gpu=use_gpu)
                    job_status = awx(incident_number,playbook)
                    while (job_status == "failed"):
                        playbook = process_playbook(description, incident_number,use_gpu=use_gpu)
                        job_status = awx(incident_number,playbook)
                    payload = {
                        'comments': playbook
                    }
                    response = requests.patch(update_url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
                    if response.status_code != 200: 
                        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
                else:
                    url = instance + journal_endpoint
                    params = {
                        'sysparm_query': f'element_id={incident_sys_id}^element=comments'
                    }
                    response = requests.get(url,auth=HTTPBasicAuth(username, password),headers=headers,params=params)
                    data = response.json().get('result', [])
                    sorted_comments = sorted(data, key=lambda x: x['sys_created_on'], reverse=True)
                    latest_comment = sorted_comments[0]["value"]
                    if latest_comment == "Regenerate":
                        update_url = instance + endpoint + '/' + incident_sys_id
                        payload = {
                            'comments': 'We have received your feedback. Please be patient, and we will create another playbook.'
                        }
                        response = requests.patch(update_url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
                        if response.status_code != 200: 
                            print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
                        playbook= process_playbook(description, incident_number,use_gpu=use_gpu)
                        job_status = awx(incident_number,playbook)
                        while (job_status == "failed"):
                            playbook = process_playbook(description, incident_number,use_gpu=use_gpu)
                            job_status = awx(incident_number,playbook)
                        payload = {
                        'comments': playbook
                        }
                        response = requests.patch(update_url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
                        if response.status_code != 200: 
                            print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
    
    else:
        print(f"Error: {response.status_code}, {response.text}")

    # Wait 0.2 seconds before checking for new incidents again
    time.sleep(0.2)
    
