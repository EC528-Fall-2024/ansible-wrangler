from openai import OpenAI
import logging
import os
import git
import requests
import sys
from datetime import datetime
import shutil
import time
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# Read the OpenAI API key and GitHub token from environment variables
OpenAI.api_key = os.getenv('OPENAI_API_KEY')
# github_token = os.getenv('GITHUB_TOKEN')
username = os.getenv('SN_USERNAME')
password = os.getenv('SN_PASSWORD')

instance = "https://dev262513.service-now.com"
client = OpenAI()

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL to find the user sys_id
user_name = 'System Administrator'
url = f"{instance}{user_endpoint}?sysparm_query=name={user_name}"

# ServiceNow instance URL and endpoint for the incidents table
# SN_URL = "https://dev262513.service-now.com"
# SN_PARAMS = {
#     'sysparm_query': 'caller_id.name=System Administrator',
#     'sysparm_limit': 1
# }
# SN_HEADERS = {
#     'Accept': 'application/json',
#     'Content-Type': 'application/json'
# }

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


# State ID for "Awaiting User Info". You need to replace this with the actual value.
# AWAITING_USER_INFO_STATE_ID = 'your_awaiting_user_info_state_id'

# GitHub repository URL for existing playbooks
EXISTING_PLAYBOOKS_REPO_URL = "https://github.com/EC528-Fall-2024/ansible-wrangler.git"
EXISTING_PLAYBOOKS_DIR = "existing_playbooks"

# Set up logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

def get_most_recent_incident():
    logger.info("Making a call to ServiceNow to check for incidents created by System Administrator.")
    try:
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Raises an error for bad responses
        data = response.json()

        if data['result']:
            caller_sys_id = data['result'][0]['sys_id']
            print("Caller sys_id:", caller_sys_id)
        else:
            print("User not found")
            caller_sys_id = None
    except Exception as e:
        print(f"An error occurred while fetching sys_id: {e}")
        caller_sys_id = None

    # Proceed if we have the sys_id
    if caller_sys_id:
        # Updated filter query using the sys_id
        filter_query = f"caller_id={caller_sys_id}^active=true^universal_requestISEMPTY"
        incidents_url = f"{instance}{endpoint}?sysparm_query={filter_query}"

        try:
            response = requests.get(incidents_url, headers=headers, auth=HTTPBasicAuth(username, password))
            response.raise_for_status()
            data = response.json()

            if data['result']:
                for incident in data['result']:
                    incident_description = incident.get('short_description', 'default')
                    print(f"Incident Description: {incident_description}")

                    # Search for playbooks related to the incident description
                    print("Searching for playbooks related to the incident description...")
                    matching_playbooks = search_existing_playbooks(incident_description)
    #                 if matching_playbooks:
    #                     for match in matching_playbooks:
    #                         print(f"Found in file: {match['file']}")
    #                         if 'task' in match:
    #                             print(f"Task: {match['task']}")
    #                 else:
    #                     print("No matching playbooks found.")
    #         else:
    #             print("No incidents found.")
        except Exception as e:
            print(f"An error occurred when querying incidents: {e}")
    # else:
    #     print("Cannot proceed without a valid sys_id")

def ask_openai(description):
    logger.info(f"Generating Ansible playbook for description: {description}")
    response = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are an expert in writing Ansible playbooks. You do not need any help in explaining the playbook or how to run the playbook. You return amazing playbooks that always work."},
        {"role": "user", "content": f"Create an Ansible playbook based on this incident description: {description}"}
    ])
    playbook_content = response.choices[0].message.content.strip()
    logger.info(f"Generated playbook content: {playbook_content}")
    return playbook_content

# def format_playbook_content(content):
#     # Add YAML document marker '---' at the beginning and remove markdown code block markers
#     content = '---\n' + content.replace('```yaml', '').replace('```', '').strip()
#     return content

def clone_existing_playbooks_repo():
    if os.path.isdir(EXISTING_PLAYBOOKS_DIR):
        shutil.rmtree(EXISTING_PLAYBOOKS_DIR)
    git.Repo.clone_from(EXISTING_PLAYBOOKS_REPO_URL, EXISTING_PLAYBOOKS_DIR)

def search_existing_playbooks(description):
    clone_existing_playbooks_repo()
    logger.info("Searching for existing playbooks.")
    existing_playbooks = []
    for root, _, files in os.walk(EXISTING_PLAYBOOKS_DIR):
        for file in files:
            if file.endswith(".yml") or file.endswith(".yaml"):
                with open(os.path.join(root, file), 'r') as f:
                    playbook_content = f.read()
                    existing_playbooks.append(playbook_content)

    for playbook in existing_playbooks:
        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert in Ansible playbooks. Evaluate if the provided playbook content matches the given incident description."},
            {"role": "user", "content": f"Incident description: {description}"},
            {"role": "assistant", "content": playbook}
        ])
        evaluation = response.choices[0].message.content.strip()
        if "matches" in evaluation.lower():
            return playbook

    return None

# def create_pull_request(branch_name, file_path, playbook_content):
#     # repo_url = 'git@github.com:cooktheryan/wranger-out.git'
#     repo_dir = 'repo'
#     # pr_url = "https://api.github.com/repos/cooktheryan/wranger-out/pulls"

#     try:
#         # Clone the repository
#         logger.info(f"Cloning repository from {repo_url}")
#         git.Repo.clone_from(repo_url, repo_dir, branch='main')
#         repo = git.Repo(repo_dir)

#         # Create a new branch
#         logger.info(f"Creating new branch: {branch_name}")
#         new_branch = repo.create_head(branch_name)
#         new_branch.checkout()

#         # Write the formatted playbook content to a file
#         with open(f"{repo_dir}/{file_path}", "w") as file:
#             file.write(playbook_content)

#         # Commit and push changes
#         repo.index.add([file_path])
#         repo.index.commit("Add generated playbook")
#         origin = repo.remote(name='origin')
#         origin.push(branch_name)

#         # Create a pull request
#         pr_title = "Add generated playbook"
#         pr_body = "This PR contains a generated Ansible playbook."
#         headers = {
#             'Authorization': f'token {github_token}',
#             'Accept': 'application/vnd.github.v3+json'
#         }
#         payload = {
#             'title': pr_title,
#             'body': pr_body,
#             'head': branch_name,
#             'base': 'main'
#         }
#         logger.info(f"Creating pull request with payload: {payload}")
#         response = requests.post(pr_url, json=payload, headers=headers)
#         logger.info(f"Pull request creation response status code: {response.status_code}")
#         if response.status_code == 201:
#             return response.json()
#         else:
#             logger.error(f"Failed to create pull request: {response.text}")
#             return None
#     finally:
#         # Ensure the local repository directory is removed
#         if os.path.isdir(repo_dir):
#             shutil.rmtree(repo_dir)

# def update_incident_state(incident_sys_id, state_id, comment=None):
#     update_url = f"{SN_URL}/{incident_sys_id}"
#     data = {
#         'state': state_id
#     }
#     if comment:
#         data['comments'] = comment

#     logger.info(f"Updating incident {incident_sys_id} to state {state_id}.")
#     try:
#         response = requests.patch(update_url, json=data, headers=SN_HEADERS, auth=HTTPBasicAuth(sn_username, sn_password))
#         logger.info(f"ServiceNow update response status code: {response.status_code}")
#         response.raise_for_status()
#         logger.info(f"Incident updated successfully.")
#     except requests.exceptions.HTTPError as http_err:
#         logger.error(f"HTTP error occurred while updating incident: {http_err}")
#     except Exception as err:
#         logger.error(f"Other error occurred while updating incident: {err}")

def process_incidents():
    while True:
        try:
            # Get the most recent incident from ServiceNow
            logger.info("Starting incident processing cycle.")
            most_recent_incident = get_most_recent_incident()
            if not most_recent_incident:
                logger.info("No incidents found.")
                # time.sleep(5)
                # continue
                break

#             description = most_recent_incident.get('description')
#             incident_sys_id = most_recent_incident.get('sys_id')

#             if not description:
#                 logger.info("No description found for the incident.")
#                 time.sleep(5)
#                 continue

#             # Check if an existing playbook matches the incident description
#             existing_playbook = search_existing_playbooks(description)
#             if existing_playbook:
#                 logger.info("Found an existing playbook that matches the incident description.")
#                 update_incident_state(incident_sys_id, AWAITING_USER_INFO_STATE_ID, comment=f"Use the following playbook: {EXISTING_PLAYBOOKS_REPO_URL}")
#                 continue

#             # Get playbook content from OpenAI based on incident description
#             playbook_content = ask_openai(description)

#             # Format the playbook content
#             formatted_content = format_playbook_content(playbook_content)

#             # Generate branch name
#             branch_name = f"generated-playbook-{datetime.now().strftime('%Y%m%d%H%M%S')}"
#             file_path = "generated_playbook.yml"

#             # Create a pull request
#             pr_response = create_pull_request(branch_name, file_path, formatted_content)

#             if pr_response:
#                 logger.info(f"Pull request created: {pr_response['html_url']}")
#                 # Update the incident state to "Awaiting User Info"
#                 update_incident_state(incident_sys_id, AWAITING_USER_INFO_STATE_ID)
#             else:
#                 logger.error('Failed to create pull request.')

        except Exception as e:
            logger.error(f"Error processing request: {e}")

#         # Sleep for 5 seconds before the next iteration
#         time.sleep(5)

if __name__ == "__main__":
    process_incidents()