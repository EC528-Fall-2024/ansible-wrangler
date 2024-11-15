import requests
from requests.auth import HTTPBasicAuth
import os
import subprocess
from dotenv import load_dotenv
from llama_interface import generate_ansible_playbook, evaluate_playbooks_with_llama
from awx import create_job_template, launch_job, track_job, trigger_project_update
import time
import logging
import sys

#things to remeber, I changed the password in authenticate user so make sure to change them back or something idk also changed it so that it walways generates playbooks

# Load environment variables
load_dotenv(override=True)

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

# Constants for ServiceNow and GitHub details
instance = os.getenv("INSTANCE")
endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'
SN_URL=f'{instance}/api/now/table/incident'
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

git_repo_url = os.getenv("GITHUB_URL")
branch = os.getenv("BRANCH")
existing_directory = os.getenv("EXISTING_DIRECTORY")
out_directory = os.getenv("OUT_DIRECTORY")

def authenticate_user():
    """Prompt for ServiceNow credentials and attempt to authenticate the user."""
    username = "admin"
    password = "$1sh2t+VcALL"
    # Attempt to fetch user details to verify credentials
    url = f"{instance}{user_endpoint}?sysparm_query=user_name={username}"
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
    
    if response.status_code == 200 and response.json()['result']:
        user_info = response.json()['result'][0]
        print("Authentication successful.")
        return username, password, user_info['sys_id']
    else:
        print("Authentication failed. Please try again.")
        return None, None, None

def fetch_incidents(username, password, state):
    """Retrieve incidents associated with the authenticated user."""
    url = SN_URL
    params = {
        'sysparm_limit': '100',  # Adjust limit as needed
        'sysparm_query': f'state{state}',
    }

    response = requests.get(url, auth=HTTPBasicAuth(username, password), params=params)
    
    if response.status_code == 200:
        incidents = response.json()['result']
        if not incidents:
            print("No incidents found for this user.")
        return incidents
    else:
        print(f"Error retrieving incidents: {response.status_code}, {response.text}")
        return []

def process_incident(incident, username, password):
    """Process a single incident by evaluating playbooks and optionally creating or running a new playbook."""
    description = incident.get("description")
    short_description = incident.get("short_description")
    incident_number = incident.get("number")

    print(f"\nProcessing Incident {incident_number}:")
    print(f"Short Description: {short_description}")
    print(f"Description: {description}")

    while True:
        # Evaluate existing playbooks from GitHub

        print("here")
        matched_playbook = evaluate_playbooks_with_llama(
            git_repo_url,
            branch,
            existing_directory,
            short_description
        )
        print(not matched_playbook) #come back and fix this matching playbook issue
        print("printing playbook below")
        print(matched_playbook)
        if not matched_playbook:
            # Generate a new playbook if no match is found
            print("No existing playbook found, generating new playbook.")
            playbook = generate_ansible_playbook(description)
            playbook_filename = f"playbook_{incident_number}.yml"
        else:
            # Use the matched playbook
            playbook = matched_playbook
            playbook_filename = f"matched_playbook_{incident_number}.yml"

        # Display playbook content to the user
        print(f"\nProposed playbook for incident {incident_number}:\n")
        print(playbook)

        # Prompt user to accept or reject the proposed playbook
        user_response = input("\nDo you accept this playbook? (y to accept / r to reject and try another): ").strip().lower()

        if user_response == 'y':
            # Save the accepted playbook to the output directory
            repo_path = os.path.abspath('.')
            saved_directory = os.path.join(repo_path, out_directory)
            os.makedirs(saved_directory, exist_ok=True)
            playbook_path = os.path.join(saved_directory, playbook_filename)

            with open(playbook_path, 'w') as f:
                f.write(playbook)

            # Commit and push the accepted playbook to Git
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
            print("\nIncident details processed:")
            print("Description:", output["short_description"])
            print("Incident Number:", output["number"])
            print("Suggested Playbook:\n", playbook)
            print("Job completed with status:", job_status)
            break  # Exit the loop after successful acceptance and processing

        elif user_response == 'r':
            print("Generating or fetching another playbook...\n")
            continue  # Go back to the top of the loop to try another playbook

        else:
            print("Invalid input. Please enter 'y' to accept or 'r' to reject.")

def update_incident_state(incident, state_id, user, password, comment=None ):
    incident_sys_id = incident.get("sys_id")
    update_url = f"{SN_URL}/{incident_sys_id}"
    data = {
        'state': state_id
    }
    if comment:
        data['comments'] = comment

    logger.info(f"Updating incident {incident_sys_id} to state {state_id}.")
    try:
        response = requests.patch(update_url, json=data, headers=headers, auth=HTTPBasicAuth(user, password))
        logger.info(f"ServiceNow update response status code: {response.status_code}")
        response.raise_for_status()
        logger.info(f"Incident updated successfully.")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while updating incident: {http_err}")
    except Exception as err:
        logger.error(f"Other error occurred while updating incident: {err}")

def main():
    """Main loop for authentication and incident processing."""
    while True:
        # Authenticate the user
        username, password, caller_sys_id = authenticate_user()
        if not username:
            continue

        while True:
            # Fetch incidents for the user
            incidents = fetch_incidents(username, password, '1')
            if not incidents:
                print("No incidents found. Waiting for 10 seconds before retrying...")
                time.sleep(10)  # Wait for 10 seconds
                continue  # Restart the loop

            # Process each incident
            for incident in incidents:
                print("here")
                update_incident_state(incident,'2', username, password, f'{username} is picking up incident {incident}')
                process_incident(incident, username, password)

            # Ask if the user wants to check for new incidents
            check_more = input("\nCheck for new incidents? (y/n): ").strip().lower()
            if check_more != 'y':
                print("Logging out...")
                break

# Run the main service loop
if __name__ == "__main__":
    main()