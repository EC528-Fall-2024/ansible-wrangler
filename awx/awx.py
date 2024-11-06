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
PLAYBOOK_NAME = os.getenv("PLAYBOOK_NAME").strip()

# Headers for authentication
headers = {
    "Authorization": f"Bearer {AWX_TOKEN}",
    "Content-Type": "application/json"
}

def get_job_template_id_by_name(name):
    params = {'name': name}
    response = requests.get(f"{AWX_URL}/job_templates/", headers=headers, params=params)
    response.raise_for_status()
    results = response.json()['results']
    if results:
        return results[0]['id']
    else:
        return None

def create_job_template():
    job_template_data = {
        "name": "Test Playbook Run",
        "job_type": "run",
        "inventory": INVENTORY_ID,
        "project": PROJECT_ID,
        "playbook": PLAYBOOK_NAME,
    }
    print("\nCreating job template with the following data:")
    print(f"Request Payload: {job_template_data}")
    response = requests.post(f"{AWX_URL}/job_templates/", headers=headers, json=job_template_data)
    response.raise_for_status()
    return response.json()['id']

def launch_job(job_template_id):
    print(f"\nLaunching job using Job Template ID: {job_template_id}")
    response = requests.post(f"{AWX_URL}/job_templates/{job_template_id}/launch/", headers=headers)
    response.raise_for_status()
    return response.json()['job']

def track_job(job_id):
    print(f"\nTracking Job ID: {job_id}")
    while True:
        response = requests.get(f"{AWX_URL}/jobs/{job_id}/", headers=headers)
        response.raise_for_status()
        status = response.json()['status']
        if status in ['successful', 'failed', 'error', 'canceled']:
            return status
        print(f"Job status: {status}...")
        time.sleep(5)  # poll every 5 seconds

def main():
    try:
        # Print initial configuration
        print("Starting AWX Job Execution with the following configuration:")
        print(f"AWX URL: {AWX_URL}")
        print(f"Project ID: {PROJECT_ID}")
        print(f"Inventory ID: {INVENTORY_ID}")
        print(f"Playbook Name: {PLAYBOOK_NAME}")

        # Check for existing job template
        job_template_id = get_job_template_id_by_name("Test Playbook Run")
        if job_template_id:
            print(f"\nFound existing job template with ID: {job_template_id}")
        else:
            # Create job template
            job_template_id = create_job_template()
            print(f"\nJob template created with ID: {job_template_id}")

        # Launch job
        job_id = launch_job(job_template_id)
        print(f"\nJob launched with ID: {job_id}")

        # Track job status
        status = track_job(job_id)
        print(f"\nJob completed with status: {status}")

    except requests.RequestException as e:
        print(f"\nError: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    main()
