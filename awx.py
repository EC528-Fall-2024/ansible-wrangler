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
        "playbook": playbook_name,  # Ensure this is the correct relative path in the project
    }
    print("\nCreating job template with the following data:")
    print(f"Request Payload: {job_template_data}")

    try:
        response = requests.post(f"{AWX_URL}/job_templates/", headers=headers, json=job_template_data)
        response.raise_for_status()
        return response.json()['id']
    except requests.exceptions.HTTPError as e:
        # Print the error message and response content for debugging
        print(f"Failed to create job template. Error: {e}")
        print(f"Response content: {e.response.text}")
        raise

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

## Testing

# Mock environment setup (ensure your .env file is correctly set up or substitute here if necessary)
project_id = PROJECT_ID  # Use a valid project ID or fallback for testing
playbook_name = "wrangler_out/matched_playbook_INC0010026.yml"  # Set relative path to playbook within wrangler_out

try:
    # Step 1: Trigger project update in AWX to ensure the latest playbooks are in sync
    print("\nStarting test for AWX functions...\n")
    trigger_project_update(project_id)

    # Step 2: Create a job template for the playbook (if it doesn’t already exist)
    print("\nCreating job template for playbook execution...")
    job_template_id = create_job_template(playbook_name)
    print(f"Job Template ID: {job_template_id}")

    # Step 3: Launch the job using the job template created above
    print("\nLaunching job...")
    job_id = launch_job(job_template_id)
    print(f"Job ID: {job_id}")

    # Step 4: Track the job status until it completes
    print("\nTracking job status until completion...")
    job_status = track_job(job_id)
    print(f"Job completed with status: {job_status}")

    # Step 5: Output for validation
    print("\nTest Output:")
    output = {
        "playbook_name": playbook_name,
        "job_template_id": job_template_id,
        "job_id": job_id,
        "job_status": job_status
    }
    print(output)

except Exception as e:
    print(f"Test failed with error: {e}")
