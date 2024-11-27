import os
import requests
from requests.auth import HTTPBasicAuth
import time
from dotenv import load_dotenv
from llama_interface import (
    generate_ansible_playbook,
    load_retrieval_system,
    retrieve_playbooks,
    FAISS_INDEX_PATH,
    DOCUMENTS_PATH
)
from awx import create_job_template, launch_job, track_job, trigger_project_update
from utils import check_gpu_availability

# Suppress TOKENIZERS_PARALLELISM warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables
load_dotenv(override=True)

# Check GPU availability
use_gpu = check_gpu_availability()
print(f'GPU Available: {use_gpu}')

# ServiceNow API details
instance = os.getenv("INSTANCE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
ssh_credential_id = int(os.getenv("CREDENTIAL_ID"))
server_limit = os.getenv("SERVER_LIMIT")
journal_endpoint = '/api/now/table/sys_journal_field'
incident_endpoint = '/api/now/table/incident'
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# GitHub details
branch = os.getenv("BRANCH") or "rag_cloud"
out_directory = os.getenv("OUT_DIRECTORY") or "wrangler_out"

# Track incidents
tracked_incidents = {}

# Load FAISS retrieval system
if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCUMENTS_PATH):
    print("Loading retrieval system...")
    load_retrieval_system(use_gpu=use_gpu)
else:
    print("FAISS index or documents not found. Please run the indexing step first.")

def fetch_unresolved_incidents():
    filter_query = "state!=6^active=true^sysparm_fields=number,sys_id,state,short_description"
    url = f"{instance}{incident_endpoint}?sysparm_query={filter_query}"
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
    response.raise_for_status()
    return response.json().get("result", [])

def update_incident(incident_sys_id, payload):
    url = f"{instance}{incident_endpoint}/{incident_sys_id}"
    response = requests.patch(url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
    print(url)
    print(response)
    response.raise_for_status()
    print(f"Updated Incident {incident_sys_id}: {payload}")

def fetch_latest_comment(incident_sys_id, last_comment_id=None):
    url = f"{instance}{journal_endpoint}"
    params = {"sysparm_query": f"element_id={incident_sys_id}^element=comments"}
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password), params=params)
    response.raise_for_status()
    comments = response.json().get("result", [])
    if comments:
        latest_comment = sorted(comments, key=lambda x: x["sys_created_on"], reverse=True)[0]
        if latest_comment["sys_id"] != last_comment_id:
            return latest_comment["value"].strip().lower(), latest_comment["sys_id"]
    return None, last_comment_id

def execute_playbook_on_awx(incident_number, playbook):
    from pathlib import Path
    import subprocess

    playbook_filename = f"playbook_{incident_number}.yml"
    repo_path = Path.cwd()
    saved_directory = repo_path / out_directory
    saved_directory.mkdir(parents=True, exist_ok=True)
    playbook_path = saved_directory / playbook_filename

    try:
        with playbook_path.open("w", encoding="utf-8") as file:
            file.write(playbook)
        print(f"Playbook saved to {playbook_path}")
    except Exception as e:
        print(f"Error saving playbook: {e}")
        return "failed"

    try:
        print(f"Committing and pushing playbook {playbook_filename} to Git...")
        subprocess.run(["git", "add", str(playbook_path)], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", f"Add playbook for incident {incident_number}"], cwd=repo_path, check=True)
        subprocess.run(["git", "push", "origin", branch], cwd=repo_path, check=True)
        print("Playbook committed and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        return "failed"

    project_id = int(os.getenv("PROJECT_ID"))
    try:
        print("Triggering project update in AWX...")
        trigger_project_update(project_id)
        print("AWX project update triggered successfully.")
    except Exception as e:
        print(f"Error triggering project update in AWX: {e}")
        return "failed"

    awx_playbook_path = f"{out_directory}/{playbook_filename}"
    try:
        print(f"Creating AWX job template for playbook: {awx_playbook_path}")
        job_template_id = create_job_template(awx_playbook_path, ssh_credential_id)
        print(f"AWX job template created with ID: {job_template_id}")
    except Exception as e:
        print(f"Error creating AWX job template: {e}")
        return "failed"

    try:
        print(f"Launching AWX job using template ID: {job_template_id}")
        job_id = launch_job(job_template_id=job_template_id, ssh_credential_id=ssh_credential_id, limit=server_limit)
        print(f"AWX job launched with ID: {job_id}")
    except Exception as e:
        print(f"Error launching AWX job: {e}")
        return "failed"

    try:
        print(f"Tracking job ID: {job_id} on AWX...")
        job_status = track_job(job_id)
        print(f"AWX job completed with status: {job_status}")
        return job_status
    except Exception as e:
        print(f"Error tracking AWX job: {e}")
        return "failed"

def generate_or_retrieve_playbooks(task_description, regenerate_with_ai=False):
    print(f"Generating or retrieving playbooks for task: {task_description}")
    if regenerate_with_ai:
        return [generate_ansible_playbook(task_description, regenerate_with_ai=True, use_gpu=use_gpu)]
    else:
        retrieved_playbooks = retrieve_playbooks(task_description, top_k=3, use_gpu=use_gpu)
        if retrieved_playbooks:
            print("Retrieved Playbooks:")
            for idx, pb in enumerate(retrieved_playbooks, 1):
                print(f"Playbook {idx}:\n{pb}\n")
            return retrieved_playbooks
        else:
            print("No relevant playbooks found. Generating a new playbook.")
            return [generate_ansible_playbook(task_description, regenerate_with_ai=True, use_gpu=use_gpu)]

# Main processing loop
print("Starting Wrangler...")
while True:
    print("Fetching unresolved incidents...")
    unresolved_incidents = fetch_unresolved_incidents()

    for incident in unresolved_incidents:
        incident_sys_id = incident["sys_id"]
        incident_number = incident["number"]
        short_description = incident.get("short_description", "No description provided.")

        if incident_sys_id not in tracked_incidents:
            print(f"Sending welcome message for Incident {incident_number}")
            payload = {
                "comments": "Hello! Please respond with 'Search' to search for an existing playbook for this incident."
            }
            update_incident(incident_sys_id, payload)
            tracked_incidents[incident_sys_id] = {
                "last_comment_id": None,
                "playbooks": [],
                "state": "waiting",
            }

        session = tracked_incidents[incident_sys_id]
        latest_comment, last_comment_id = fetch_latest_comment(incident_sys_id, session["last_comment_id"])

        if latest_comment is None:
            continue

        session["last_comment_id"] = last_comment_id
        print(f"New comment for Incident {incident_number}: {latest_comment}")

        if latest_comment == "search" and session["state"] == "waiting":
            print(f"User requested playbook search for Incident {incident_number}")
            session["playbooks"] = generate_or_retrieve_playbooks(short_description)
            playbook_list = "\n\n".join([f"Playbook {idx}:\n{pb}" for idx, pb in enumerate(session["playbooks"], 1)])
            payload = {
                "comments": f"The following playbooks have been retrieved:\n\n{playbook_list}\n\n"
                            "Please respond with the number of the playbook you want to accept or 'Generate' to create a new playbook using AI.",
                "state": 2
            }
            update_incident(incident_sys_id, payload)
            session["state"] = "choose_or_generate"

        elif latest_comment == "generate" and session["state"] == "choose_or_generate":
            print(f"User requested playbook regeneration for Incident {incident_number}")
            new_playbook = generate_ansible_playbook(short_description, regenerate_with_ai=True, use_gpu=use_gpu)
            session["playbooks"].append(new_playbook)
            playbook_list = "\n\n".join([f"Playbook {idx}:\n{pb}" for idx, pb in enumerate(session["playbooks"], 1)])
            payload = {
                "comments": f"The following playbooks have been retrieved/generated:\n\n{playbook_list}\n\n"
                            "Please respond with the number of the playbook you want to accept or 'Generate' to create a new playbook using AI."
            }
            update_incident(incident_sys_id, payload)

        elif latest_comment.isdigit() and session["state"] == "choose_or_generate":
            playbook_index = int(latest_comment) - 1
            if 0 <= playbook_index < len(session["playbooks"]):
                print(f"User selected Playbook {latest_comment} for Incident {incident_number}. Deploying...")
                job_status = execute_playbook_on_awx(incident_number, session["playbooks"][playbook_index])
                if job_status == "successful":
                    print(f"AWX deployment successful for Incident {incident_number}")
                    payload = {
                        "state": 6,
                        "close_code": "Solution provided",
                        "close_notes": "Incident has been successfully resolved.",
                        "comments": "The playbook has been successfully deployed. The incident is now resolved."
                    }
                    update_incident(incident_sys_id, payload)
                    tracked_incidents.pop(incident_sys_id)
                else:
                    print(f"AWX deployment failed for Incident {incident_number}")
                    playbook_list = "\n\n".join([f"Playbook {idx}:\n{pb}" for idx, pb in enumerate(session["playbooks"], 1)])
                    payload = {
                        "comments": f"Playbook deployment failed. The following playbooks are available:\n\n{playbook_list}\n\n"
                                    "Respond with 'Generate' for a new playbook or select one of the above options."
                    }
                    update_incident(incident_sys_id, payload)

    print("Sleeping for 5 seconds...")
    time.sleep(5)
