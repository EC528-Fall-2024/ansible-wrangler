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
    print(response.json())
    response.raise_for_status()
    results = response.json()['results']
    if results:
        return results[0]['id']
    else:
        return None

def create_job_template(playbook_name, ssh_credential_id):
    """
    Creates a job template with a given playbook name and associates it with SSH credentials.
    """
    job_template_name = f"Playbook Run: {playbook_name}"
    job_template_id = get_job_template_id_by_name(job_template_name)
    if job_template_id:
        print(f"\nFound existing job template with ID: {job_template_id}")
        associate_credentials_with_template(job_template_id, ssh_credential_id)
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

    try:
        response = requests.post(f"{AWX_URL}/job_templates/", headers=headers, json=job_template_data)
        response.raise_for_status()
        job_template_id = response.json()['id']
        associate_credentials_with_template(job_template_id, ssh_credential_id)
        return job_template_id
    except requests.exceptions.HTTPError as e:
        print(f"Failed to create job template. Error: {e}")
        print(f"Response content: {e.response.text}")
        raise

def launch_job(job_template_id, ssh_credential_id, limit=None):
    """
    Launches a job based on the given job template ID, with specific SSH credentials and a server limit.
    """
    print(f"\nLaunching job using Job Template ID: {job_template_id}")
    payload = {
        "credentials": [ssh_credential_id],
    }
    if limit:
        payload["limit"] = limit

    print(f"Payload for job launch: {payload}")

    response = requests.post(
        f"{AWX_URL}/job_templates/{job_template_id}/launch/",
        headers=headers,
        json=payload
    )
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

def associate_credentials_with_template(job_template_id, ssh_credential_id):
    """
    Associates an SSH credential with the given job template ID.
    If a machine credential already exists, it skips or replaces it.
    """
    # Get existing credentials for the job template
    print(f"Fetching existing credentials for Job Template ID: {job_template_id}")
    response = requests.get(
        f"{AWX_URL}/job_templates/{job_template_id}/credentials/",
        headers=headers
    )
    response.raise_for_status()
    existing_credentials = response.json()

    # Check if a machine credential is already associated
    machine_credentials = [
        cred for cred in existing_credentials['results']
        if cred['kind'] == 'ssh'
    ]

    if machine_credentials:
        existing_cred_id = machine_credentials[0]['id']
        if existing_cred_id == ssh_credential_id:
            print(f"SSH credential (ID: {ssh_credential_id}) is already associated with Job Template ID: {job_template_id}. Skipping...")
            return
        else:
            print(f"Removing existing SSH credential (ID: {existing_cred_id})...")
            disassociate_payload = {"disassociate": True, "id": existing_cred_id}
            response = requests.post(
                f"{AWX_URL}/job_templates/{job_template_id}/credentials/",
                headers=headers,
                json=disassociate_payload
            )
            if response.status_code != 204:
                print(f"Failed to disassociate credentials. Status: {response.status_code}")
                print(f"Response: {response.text}")
                raise Exception("Error disassociating credentials from job template.")
            print(f"Removed existing SSH credential (ID: {existing_cred_id}).")

    # Associate the new SSH credential
    print(f"Associating SSH credential (ID: {ssh_credential_id}) with Job Template ID: {job_template_id}...")
    associate_payload = {"associate": True, "id": ssh_credential_id}
    response = requests.post(
        f"{AWX_URL}/job_templates/{job_template_id}/credentials/",
        headers=headers,
        json=associate_payload
    )
    if response.status_code in [200, 204]:
        print(f"Successfully associated SSH credential (ID: {ssh_credential_id}) with Job Template (ID: {job_template_id}).")
    else:
        print(f"Failed to associate credentials. Status: {response.status_code}")
        print(f"Response: {response.text}")
        raise Exception("Error associating credentials with job template.")
