import requests
from requests.auth import HTTPBasicAuth
import json
import os
import time
import subprocess
from dotenv import load_dotenv
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
from awx import create_job_template, launch_job, track_job, trigger_project_update

# Load environment variables
load_dotenv(override=True)

# Connect to ServiceNow API
instance = os.getenv("INSTANCE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = "System Administrator" ## UPDATE USER
incident_number = os.getenv("INCIDENT")
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
seen_instances = set()
# Fetch incident data
while True:
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
            
            # Check if incident is already processed
            if incident_number in seen_instances:
                continue  # Skip if already seen
            else:
                seen_instances.add(incident_number)  # Mark incident as seen

                description = incident.get("description")
                short_description = incident.get("short_description")

                # Evaluate existing playbooks from GitHub
                matched_playbook = evaluate_playbooks_with_llama(
                    git_repo_url,
                    branch,
                    existing_directory,
                    short_description
                )

                if matched_playbook is None:
                    # Generate a new playbook if no match is found
                    print("Generating new playbook.")
                    playbook = generate_ansible_playbook(description)
                    playbook_filename = f"playbook_{incident_number}.yml"
                else:
                    # Use the matched playbook
                    playbook = matched_playbook
                    playbook_filename = f"matched_playbook_{incident_number}.yml"

                # Save the playbook to the output directory in the Git repository
                repo_path = os.path.abspath('.')
                saved_directory = os.path.join(repo_path, out_directory)
                os.makedirs(saved_directory, exist_ok=True)
                playbook_path = os.path.join(saved_directory, playbook_filename)

                with open(playbook_path, 'w') as f:
                    f.write(playbook)

                # Commit and push the new playbook to the Git repository
                subprocess.run(['git', 'add', playbook_path], cwd=repo_path)
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

                # Output the result details
                output = {
                    "short_description": short_description,
                    "description": description,
                    "number": incident_number,
                    "state": incident.get("state"),
                    "suggested_playbook": playbook,
                    "job_status": job_status
                }
                print("\n\nIncident details:")
                print("User: ", user_name)
                print("Description: ", output["short_description"])
                print("Incident Number: ", output["number"])
                print("\n\nSuggested playbook:")
                print("Playbook:\n", playbook)
                print(f"\nJob completed with status: {job_status}")

    else:
        print(f"Error: {response.status_code}, {response.text}")

    # Wait 0.2 seconds before checking for new incidents again
    time.sleep(0.2)
