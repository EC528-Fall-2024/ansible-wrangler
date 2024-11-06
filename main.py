# import requests
# from requests.auth import HTTPBasicAuth
# import json
# from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama

# # Connect to ServiceNow API
# # ServiceNow Instance Profile
# instance = 'https://dev248794.service-now.com'
# username = 'admin'
# password = '$1sh2t+VcALL'

# endpoint = '/api/now/table/incident'
# user_endpoint = '/api/now/table/sys_user'

# # Form the complete URL with filters and ordering by number in ascending order
# user_name = 'System Administrator'  # desired user name to find the sys_id
# incident_number = 'INC0010013'  # desired incident number to find the playbook for
# url = instance + user_endpoint + "?sysparm_query=name=" + user_name

# headers = {
#     "Content-Type": "application/json",
#     "Accept": "application/json"
# }

# # Fetch user sys_id
# response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

# if response.status_code == 200:
#     data = response.json()
#     if len(data['result']) > 0:
#         caller_sys_id = data['result'][0]['sys_id']
#         print("Caller sys_id:", caller_sys_id)
#     else:
#         print("User not found")
#         exit()
# else:
#     print(f"Error: {response.status_code}, {response.text}")
#     exit()

# # Updated filter query using the sys_id
# filter_query = f"caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
# url = instance + endpoint + "?sysparm_query=" + filter_query

# # Fetch incident data
# response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

# if response.status_code == 200:
#     data = response.json()
    
#     # If no incidents are found
#     if len(data['result']) == 0:
#         print("No incidents found for the user.")
    
#     # Output required fields for each incident
#     for incident in data['result']:
#         if incident.get("number") == incident_number:
#             description = incident.get("description")
#             short_description = incident.get("short_description")

#             # Define GitHub repository details
#             git_repo_url = 'https://github.com/EC528-Fall-2024/ansible-wrangler.git' ## GITHUB URL
#             branch = 'Mac-New' ## BRANCH
#             directory = 'existing_playbooks' ## DIRECTORY

#             # Evaluate existing playbooks from GitHub
#             matched_playbook = evaluate_playbooks_with_llama(
#                 git_repo_url,
#                 branch,
#                 directory,
#                 short_description
#             )

#             if matched_playbook is None:
#                 # Generate a new playbook if no match is found
#                 playbook = generate_ansible_playbook(description)
#             else:
#                 playbook = matched_playbook

#             output = {
#                 "short_description": short_description,
#                 "description": description,
#                 "number": incident.get("number"),
#                 "state": incident.get("state"),
#                 "suggested_playbook": playbook
#             }
#             print("\n\nIncident details:")
#             print("User: ", user_name)
#             print("Description: ", output["short_description"])
#             print("Incident Number: ", output["number"])
#             print("\n\nSuggested playbook:")
#             print("Playbook:\n", playbook)
# else:
#     print(f"Error: {response.status_code}, {response.text}")


import requests
from requests.auth import HTTPBasicAuth
import json
import os
import subprocess
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
from awx import create_job_template, launch_job, track_job, trigger_project_update

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
            git_repo_url = 'https://github.com/EC528-Fall-2024/ansible-wrangler.git'  # GitHub URL
            branch = 'Mac-New'  # Branch
            directory = 'existing_playbooks'  # Directory

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
                # Save the new playbook to the Git repository
                playbook_filename = f"playbook_{incident_number}.yml"
                # saved_directory = "{directory}/wrangler_out"
                repo_path = os.path.abspath('.')
                saved_directory = os.path.join(repo_path, 'wrangler_out')
                # playbook_path = os.path.join('path_to_local_git_repo', saved_directory, playbook_filename)
                playbook_path = os.path.join(saved_directory, playbook_filename)
                with open(playbook_path, 'w') as f:
                    f.write(playbook)
                # Commit and push the new playbook to the Git repository
                subprocess.run(['git', 'add', playbook_path], cwd='repo_path')
                subprocess.run(['git', 'commit', '-m', f'Add playbook for incident {incident_number}'], cwd='repo_path')
                subprocess.run(['git', 'push', 'origin', branch], cwd='repo_path')
            else:
                playbook = matched_playbook
                # Extract the playbook filename from the matched playbook
                # This assumes the playbook content includes a comment with its filename
                playbook_filename = f"playbook_{incident_number}.yml"
                repo_path = os.path.abspath('.')
                saved_directory = os.path.join(repo_path, 'wrangler_out')
                playbook_path = os.path.join(saved_directory, playbook_filename)

                with open(playbook_path, 'w') as f:
                    f.write(playbook)
                
                subprocess.run(['git', 'add', playbook_path], cwd=repo_path)
                subprocess.run(['git', 'commit', '-m', f'Add matched playbook for incident {incident_number}'], cwd=repo_path)
                subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path)

            # Trigger project update in AWX to sync the latest playbooks
            # project_id = int(os.getenv("PROJECT_ID"))
            # trigger_project_update(project_id)

            # Use AWX to run the playbook
            job_template_id = create_job_template(playbook_filename)
            job_id = launch_job(job_template_id)
            job_status = track_job(job_id)

            output = {
                "short_description": short_description,
                "description": description,
                "number": incident.get("number"),
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
