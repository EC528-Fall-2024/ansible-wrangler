import openai
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

# Global Constants
SN_URL = "https://ansible.service-now.com/api/now/table/incident"
EXISTING_PLAYBOOKS_REPO_URL = "https://github.com/cooktheryan/existing-playbooks.git"
EXISTING_PLAYBOOKS_DIR = "existing_playbooks"
PR_URL = "https://api.github.com/repos/cooktheryan/wranger-out/pulls"
REPO_URL = 'git@github.com:cooktheryan/wranger-out.git'
REPO_DIR = 'repo'
AWAITING_USER_INFO_STATE_ID = 'your_awaiting_user_info_state_id'  # Replace with actual value

# Set up logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def setup_environment_variables():
    """Read API keys and credentials from environment variables."""
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Fetch environment variables
        openai.api_key = os.getenv('OPENAI_API_KEY')
        github_token = os.getenv('GITHUB_TOKEN')
        sn_username = os.getenv('SN_USERNAME')
        sn_password = os.getenv('SN_PASSWORD')

        if not all([openai.api_key, github_token, sn_username, sn_password]):
            logger.error("Missing required environment variables.")
            raise EnvironmentError("One or more required environment variables are missing.")
        
        return github_token, sn_username, sn_password
    except Exception as e:
        logger.error(f"Error setting up environment variables: {e}")
        sys.exit(1)

def get_service_now_incident(sn_username, sn_password):
    """Fetch the most recent incident from ServiceNow."""
    params = {
        'sysparm_query': 'caller_id.name=Roger Lopez^ORDERBYDESCsys_created_on',
        'sysparm_limit': 1
    }
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    logger.info("Fetching the most recent incident from ServiceNow.")
    
    try:
        response = requests.get(SN_URL, params=params, headers=headers, auth=HTTPBasicAuth(sn_username, sn_password))
        response.raise_for_status()
        incidents = response.json().get('result', [])
        logger.info(f"ServiceNow response: {incidents}")
        return incidents[0] if incidents else None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error while fetching ServiceNow incident: {req_err}")
    except Exception as err:
        logger.error(f"An error occurred while fetching ServiceNow incident: {err}")
    return None

def ask_openai_for_playbook(description):
    """Use OpenAI to generate an Ansible playbook based on an incident description."""
    logger.info(f"Generating Ansible playbook for incident: {description}")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in writing Ansible playbooks."},
                {"role": "user", "content": f"Create an Ansible playbook for this incident: {description}"}
            ]
        )
        playbook_content = response['choices'][0]['message']['content'].strip()
        logger.info(f"Generated playbook: {playbook_content}")
        return playbook_content
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when generating playbook: {e}")
    return None

def format_playbook(playbook_content):
    """Format the playbook content to adhere to YAML standards."""
    logger.info("Formatting playbook content.")
    return f"---\n{playbook_content.replace('```yaml', '').replace('```', '').strip()}"

def clone_existing_playbooks_repo():
    """Clone the existing playbooks repository from GitHub."""
    logger.info("Cloning existing playbooks repository.")
    try:
        if os.path.isdir(EXISTING_PLAYBOOKS_DIR):
            shutil.rmtree(EXISTING_PLAYBOOKS_DIR)
        git.Repo.clone_from(EXISTING_PLAYBOOKS_REPO_URL, EXISTING_PLAYBOOKS_DIR)
    except git.GitError as e:
        logger.error(f"Git error during cloning: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during repository cloning: {e}")

def search_existing_playbooks(description):
    """Search for existing playbooks in the cloned repository."""
    try:
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
            match = evaluate_playbook_match(playbook, description)
            if match:
                return playbook
        return None
    except Exception as e:
        logger.error(f"Error while searching existing playbooks: {e}")
        return None

def evaluate_playbook_match(playbook, description):
    """Use OpenAI to evaluate if the playbook matches the incident description."""
    logger.info("Evaluating playbook match.")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Evaluate if the playbook matches the incident description."},
                {"role": "user", "content": f"Incident: {description}"},
                {"role": "assistant", "content": playbook}
            ]
        )
        evaluation = response['choices'][0]['message']['content'].strip()
        return "matches" in evaluation.lower()
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error during playbook match evaluation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during playbook match evaluation: {e}")
    return False

def create_pull_request(branch_name, file_path, playbook_content, github_token):
    """Create a pull request in the GitHub repository with the generated playbook."""
    try:
        repo = clone_repository(REPO_URL, REPO_DIR)
        new_branch = create_branch(repo, branch_name)
        write_playbook_to_file(REPO_DIR, file_path, playbook_content)
        commit_and_push_changes(repo, file_path, new_branch, github_token)
        return submit_pull_request(branch_name, github_token)
    except Exception as e:
        logger.error(f"Error during pull request creation: {e}")
    finally:
        cleanup_local_repo(REPO_DIR)

# Other utility functions remain the same...

def process_incidents():
    """Main loop for processing incidents."""
    github_token, sn_username, sn_password = setup_environment_variables()

    while True:
        incident = get_service_now_incident(sn_username, sn_password)
        if not incident:
            logger.info("No incident found. Retrying in 5 seconds.")
            time.sleep(5)
            continue
        
        incident_sys_id = incident['sys_id']
        description = incident['short_description']
        existing_playbook = search_existing_playbooks(description)
        
        if existing_playbook:
            logger.info("Found an existing playbook.")
            update_incident_state(sn_username, sn_password, incident_sys_id, AWAITING_USER_INFO_STATE_ID, "Existing playbook found.")
            time.sleep(5)
            continue

        playbook_content = ask_openai_for_playbook(description)
        if not playbook_content:
            logger.info("No playbook generated.")
            time.sleep(5)
            continue
        
        formatted_playbook = format_playbook(playbook_content)
        branch_name = f"add-playbook-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        file_path = f"playbooks/{branch_name}.yml"

        pr_response = create_pull_request(branch_name, file_path, formatted_playbook, github_token)
        if pr_response:
            update_incident_state(sn_username, sn_password, incident_sys_id, AWAITING_USER_INFO_STATE_ID, f"Playbook generated and PR created: {pr_response['html_url']}")
        
        time.sleep(5)

if __name__ == "__main__":
    process_incidents()
