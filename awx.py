import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWX API credentials and settings from .env
AWX_URL = os.getenv("AWX_URL").strip()
AWX_TOKEN = os.getenv("AWX_TOKEN").strip()
PROJECT_ID = int(os.getenv("PROJECT_ID"))
INVENTORY_ID = int(os.getenv("INVENTORY_ID"))

# Headers for authentication
headers = {
    "Authorization": f"Bearer {AWX_TOKEN}",
    "Content-Type": "application/json"
}

def trigger_project_update(project_id):
    print(f"\nTriggering project update for Project ID: {project_id}")
    response = requests.post(f"{AWX_URL}/projects/{project_id}/update/", headers=headers)
    response.raise_for_status()
    update_id = response.json()['id']
    # Wait for the project update to complete
    while True:
        update_response = requests.get(f"{AWX_URL}/project_updates/{update_id}/", headers=headers)
        update_response.raise_for_status()
        status = update_response.json()['status']
        if status in ['successful', 'failed', 'error', 'canceled']:
            print(f"Project update completed with status: {status}")
            if status != 'successful':
                raise Exception(f"Project update failed with status: {status}")
            break
        print(f"Project update status: {status}...")
        time.sleep(5)  # poll every 5 seconds

def get_job_template_id_by_name(name):
    params = {'name': name}
    response = requests.get(f"{AWX_URL}/job_templates/", headers=headers, params=params)
    response.raise_for_status()
    results = response.json()['results']
    if results:
        return results[0]['id']
    else:
        return None

def create_job_template(playbook_name):
    """
    Creates a job template with a given playbook name.
    """
    job_template_name = f"Playbook Run: {playbook_name}"
    job_template_id = get_job_template_id_by_name(job_template_name)
    if job_template_id:
        print(f"\nFound existing job template with ID: {job_template_id}")
        return job_template_id

    job_template_data = {
        "name": job_template_name,
        "job_type": "run",
        "inventory": INVENTORY_ID,
        "project": PROJECT_ID,
        "playbook": playbook_name,
    }
    print("\nCreating job template with the following data:")
    print(f"Request Payload: {job_template_data}")
    response = requests.post(f"{AWX_URL}/job_templates/", headers=headers, json=job_template_data)
    response.raise_for_status()
    return response.json()['id']

def launch_job(job_template_id):
    """
    Launches a job based on the given job template ID.
    """
    print(f"\nLaunching job using Job Template ID: {job_template_id}")
    response = requests.post(f"{AWX_URL}/job_templates/{job_template_id}/launch/", headers=headers)
    response.raise_for_status()
    return response.json()['job']

def track_job(job_id):
    """
    Tracks the job status until completion.
    """
    print(f"\nTracking Job ID: {job_id}")
    while True:
        response = requests.get(f"{AWX_URL}/jobs/{job_id}/", headers=headers)
        response.raise_for_status()
        status = response.json()['status']
        if status in ['successful', 'failed', 'error', 'canceled']:
            return status
        print(f"Job status: {status}...")
        time.sleep(5)  # poll every 5 seconds
