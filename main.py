# # import requests
# # from requests.auth import HTTPBasicAuth
# # import os
# # import subprocess
# # from dotenv import load_dotenv
# # from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
# # from awx import create_job_template, launch_job, track_job, trigger_project_update

# # # Load environment variables
# # load_dotenv()

# # # Constants for ServiceNow and GitHub details
# # instance = os.getenv("INSTANCE")
# # endpoint = '/api/now/table/incident'
# # user_endpoint = '/api/now/table/sys_user'
# # headers = {
# #     "Content-Type": "application/json",
# #     "Accept": "application/json"
# # }

# # git_repo_url = os.getenv("GITHUB_URL")
# # branch = os.getenv("BRANCH")
# # existing_directory = os.getenv("EXISTING_DIRECTORY")
# # out_directory = os.getenv("OUT_DIRECTORY")

# # def authenticate_user():
# #     """Prompt for ServiceNow credentials and attempt to authenticate the user."""
# #     username = input("Enter ServiceNow Username: ")
# #     password = input("Enter ServiceNow Password: ")
    
# #     # Attempt to fetch user details to verify credentials
# #     url = f"{instance}{user_endpoint}?sysparm_query=user_name={username}"
# #     response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
    
# #     if response.status_code == 200 and response.json()['result']:
# #         user_info = response.json()['result'][0]
# #         print("Authentication successful.")
# #         return username, password, user_info['sys_id']
# #     else:
# #         print("Authentication failed. Please try again.")
# #         return None, None, None

# # def fetch_incidents(username, password, caller_sys_id):
# #     """Retrieve incidents associated with the authenticated user."""
# #     url = f"{instance}{endpoint}?sysparm_query=caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
# #     response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
    
# #     if response.status_code == 200:
# #         incidents = response.json()['result']
# #         if not incidents:
# #             print("No incidents found for this user.")
# #         return incidents
# #     else:
# #         print(f"Error retrieving incidents: {response.status_code}, {response.text}")
# #         return []

# # def process_incident(incident, username, password):
# #     """Process a single incident by evaluating playbooks and optionally creating or running a new playbook."""
# #     description = incident.get("description")
# #     short_description = incident.get("short_description")
# #     incident_number = incident.get("number")

# #     print(f"\nProcessing Incident {incident_number}:")
# #     print(f"Short Description: {short_description}")
# #     print(f"Description: {description}")

# #     while True:
# #         # Evaluate existing playbooks from GitHub
# #         matched_playbook = evaluate_playbooks_with_llama(
# #             git_repo_url,
# #             branch,
# #             existing_directory,
# #             short_description
# #         )

# #         if matched_playbook is None:
# #             # Generate a new playbook if no match is found
# #             print("No existing playbook found, generating new playbook.")
# #             playbook = generate_ansible_playbook(description)
# #             playbook_filename = f"playbook_{incident_number}.yml"
# #         else:
# #             # Use the matched playbook
# #             playbook = matched_playbook
# #             playbook_filename = f"matched_playbook_{incident_number}.yml"

# #         # Display playbook content to the user
# #         print(f"\nProposed playbook for incident {incident_number}:\n")
# #         print(playbook)

# #         # Prompt user to accept or reject the proposed playbook
# #         user_response = input("\nDo you accept this playbook? (y to accept / r to reject and try another): ").strip().lower()

# #         if user_response == 'y':
# #             # Save the accepted playbook to the output directory
# #             repo_path = os.path.abspath('.')
# #             saved_directory = os.path.join(repo_path, out_directory)
# #             os.makedirs(saved_directory, exist_ok=True)
# #             playbook_path = os.path.join(saved_directory, playbook_filename)

# #             with open(playbook_path, 'w') as f:
# #                 f.write(playbook)

# #             # Commit and push the accepted playbook to Git
# #             subprocess.run(['git', 'add', playbook_path], cwd=repo_path)
# #             subprocess.run(['git', 'commit', '-m', f'Add playbook for incident {incident_number}'], cwd=repo_path)
# #             subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path)

# #             # Trigger project update in AWX to sync the latest playbooks
# #             project_id = int(os.getenv("PROJECT_ID"))
# #             trigger_project_update(project_id)

# #             # Set playbook path for AWX
# #             awx_playbook_path = f"{out_directory}/{playbook_filename}"

# #             # Use AWX to run the playbook
# #             job_template_id = create_job_template(awx_playbook_path)
# #             job_id = launch_job(job_template_id)
# #             job_status = track_job(job_id)

# #             # Output the result details
# #             output = {
# #                 "short_description": short_description,
# #                 "description": description,
# #                 "number": incident.get("number"),
# #                 "state": incident.get("state"),
# #                 "suggested_playbook": playbook,
# #                 "job_status": job_status
# #             }
# #             print("\nIncident details processed:")
# #             print("Description:", output["short_description"])
# #             print("Incident Number:", output["number"])
# #             print("Suggested Playbook:\n", playbook)
# #             print("Job completed with status:", job_status)
# #             break  # Exit the loop after successful acceptance and processing

# #         elif user_response == 'r':
# #             print("Generating or fetching another playbook...\n")
# #             continue  # Go back to the top of the loop to try another playbook

# #         else:
# #             print("Invalid input. Please enter 'y' to accept or 'r' to reject.")

# # def main():
# #     """Main loop for authentication and incident processing."""
# #     while True:
# #         # Authenticate the user
# #         username, password, caller_sys_id = authenticate_user()
# #         if not username:
# #             continue

# #         while True:
# #             # Fetch incidents for the user
# #             incidents = fetch_incidents(username, password, caller_sys_id)
# #             if not incidents:
# #                 break

# #             # Process each incident
# #             for incident in incidents:
# #                 process_incident(incident, username, password)

# #             # Ask if the user wants to check for new incidents
# #             check_more = input("\nCheck for new incidents? (y/n): ").strip().lower()
# #             if check_more != 'y':
# #                 print("Logging out...")
# #                 break

# # # Run the main service loop
# # if __name__ == "__main__":
# #     main()

# import requests
# from requests.auth import HTTPBasicAuth
# import os
# import subprocess
# from dotenv import load_dotenv
# from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
# from awx import create_job_template, launch_job, track_job, trigger_project_update
# from auth_listener import login_event_queue  # Import the login event queue from auth_listener

# # Load environment variables
# load_dotenv()

# # Constants for ServiceNow and GitHub details
# instance = os.getenv("INSTANCE")
# endpoint = '/api/now/table/incident'
# user_endpoint = '/api/now/table/sys_user'
# headers = {
#     "Content-Type": "application/json",
#     "Accept": "application/json"
# }

# git_repo_url = os.getenv("GITHUB_URL")
# branch = os.getenv("BRANCH")
# existing_directory = os.getenv("EXISTING_DIRECTORY")
# out_directory = os.getenv("OUT_DIRECTORY")

# def authenticate_user(username, password):
#     """Authenticate a user with ServiceNow using provided credentials."""
#     url = f"{instance}{user_endpoint}?sysparm_query=user_name={username}"
#     response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

#     if response.status_code == 200 and response.json()['result']:
#         user_info = response.json()['result'][0]
#         print("Authentication successful.")
#         return username, password, user_info['sys_id']
#     else:
#         print("Authentication failed. Please try again.")
#         return None, None, None

# def fetch_incidents(username, password, caller_sys_id):
#     """Retrieve incidents associated with the authenticated user."""
#     url = f"{instance}{endpoint}?sysparm_query=caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
#     response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
    
#     if response.status_code == 200:
#         incidents = response.json()['result']
#         if not incidents:
#             print("No incidents found for this user.")
#         return incidents
#     else:
#         print(f"Error retrieving incidents: {response.status_code}, {response.text}")
#         return []

# def process_incident(incident, username, password):
#     """Process a single incident by evaluating playbooks and optionally creating or running a new playbook."""
#     description = incident.get("description")
#     short_description = incident.get("short_description")
#     incident_number = incident.get("number")

#     print(f"\nProcessing Incident {incident_number}:")
#     print(f"Short Description: {short_description}")
#     print(f"Description: {description}")

#     while True:
#         # Evaluate existing playbooks from GitHub
#         matched_playbook = evaluate_playbooks_with_llama(
#             git_repo_url,
#             branch,
#             existing_directory,
#             short_description
#         )

#         if matched_playbook is None:
#             # Generate a new playbook if no match is found
#             print("No existing playbook found, generating new playbook.")
#             playbook = generate_ansible_playbook(description)
#             playbook_filename = f"playbook_{incident_number}.yml"
#         else:
#             # Use the matched playbook
#             playbook = matched_playbook
#             playbook_filename = f"matched_playbook_{incident_number}.yml"

#         # Display playbook content to the user
#         print(f"\nProposed playbook for incident {incident_number}:\n")
#         print(playbook)

#         # Prompt user to accept or reject the proposed playbook
#         user_response = input("\nDo you accept this playbook? (y to accept / r to reject and try another): ").strip().lower()

#         if user_response == 'y':
#             # Save the accepted playbook to the output directory
#             repo_path = os.path.abspath('.')
#             saved_directory = os.path.join(repo_path, out_directory)
#             os.makedirs(saved_directory, exist_ok=True)
#             playbook_path = os.path.join(saved_directory, playbook_filename)

#             with open(playbook_path, 'w') as f:
#                 f.write(playbook)

#             # Commit and push the accepted playbook to Git
#             subprocess.run(['git', 'add', playbook_path], cwd=repo_path)
#             subprocess.run(['git', 'commit', '-m', f'Add playbook for incident {incident_number}'], cwd=repo_path)
#             subprocess.run(['git', 'push', 'origin', branch], cwd=repo_path)

#             # Trigger project update in AWX to sync the latest playbooks
#             project_id = int(os.getenv("PROJECT_ID"))
#             trigger_project_update(project_id)

#             # Set playbook path for AWX
#             awx_playbook_path = f"{out_directory}/{playbook_filename}"

#             # Use AWX to run the playbook
#             job_template_id = create_job_template(awx_playbook_path)
#             job_id = launch_job(job_template_id)
#             job_status = track_job(job_id)

#             # Output the result details
#             output = {
#                 "short_description": short_description,
#                 "description": description,
#                 "number": incident.get("number"),
#                 "state": incident.get("state"),
#                 "suggested_playbook": playbook,
#                 "job_status": job_status
#             }
#             print("\nIncident details processed:")
#             print("Description:", output["short_description"])
#             print("Incident Number:", output["number"])
#             print("Suggested Playbook:\n", playbook)
#             print("Job completed with status:", job_status)
#             break  # Exit the loop after successful acceptance and processing

#         elif user_response == 'r':
#             print("Generating or fetching another playbook...\n")
#             continue  # Go back to the top of the loop to try another playbook

#         else:
#             print("Invalid input. Please enter 'y' to accept or 'r' to reject.")

# def monitor_login_events():
#     """Monitor the login event queue and authenticate users."""
#     while True:
#         # Wait for the next login event from the queue
#         login_event = login_event_queue.get()
#         username = login_event['user']
#         timestamp = login_event['timestamp']
#         print(f"Processing login event for {username} at {timestamp}")

#         # Prompt for password
#         password = input(f"Enter password for {username}: ")

#         # Authenticate and process incidents if successful
#         auth_result = authenticate_user(username, password)
#         if auth_result:
#             caller_sys_id = auth_result[2]
#             incidents = fetch_incidents(username, password, caller_sys_id)
#             for incident in incidents:
#                 process_incident(incident, username, password)

# # Run the login event monitor
# if __name__ == "__main__":
#     monitor_login_events()


import requests
from requests.auth import HTTPBasicAuth
import json
import os
import subprocess
from dotenv import load_dotenv
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
from awx import create_job_template, launch_job, track_job, trigger_project_update

# Load environment variables
load_dotenv()

# Connect to ServiceNow API
instance = os.getenv("INSTANCE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL with filters and ordering by number in ascending order
user_name = os.getenv("USER")
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
            # print(f"Incident Description: {description}")
            short_description = incident.get("short_description")
            # print(f"Short Description: {short_description}")

            # Evaluate existing playbooks from GitHub
            matched_playbook = evaluate_playbooks_with_llama(
                git_repo_url,
                branch,
                existing_directory,
                short_description
            )

            if matched_playbook is None:
                # Generate a new playbook if no match is found
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