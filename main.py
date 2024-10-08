import requests
from requests.auth import HTTPBasicAuth
import json
import os
import yaml
from openai import OpenAI

openai_api_key = ''
client = OpenAI(api_key=openai_api_key)

# Function to load and search playbook contents
def load_playbook(filepath):
    """Loads the playbook content from a YAML file."""
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

def search_playbook_contents(directory, search_term):
    """Searches through all playbooks in the directory for a given term."""
    matching_playbooks = []
    search_terms = [term.lower() for term in search_term.split()]  # Split the incident description into words

    # Iterate over all YAML files in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            playbook_path = os.path.join(directory, filename)
            playbook_content = load_playbook(playbook_path)

            # Search through the tasks in the playbook
            for play in playbook_content:
                tasks = play.get('tasks', [])

                # Search within tasks for partial matches
                for task in tasks:
                    task_name = task.get('name', '').lower()
                    debug_module = task.get('debug', {}).get('msg', '').lower()

                    # Check how many terms from the search term match the task name or debug message
                    task_match_count = sum(1 for term in search_terms if term in task_name)
                    debug_match_count = sum(1 for term in search_terms if term in debug_module)

                    # Require at least 2 matches for stricter relevance
                    if task_match_count >= 2 or debug_match_count >= 2:
                        matching_playbooks.append({
                            'file': filename,
                            'task': task
                        })

    return matching_playbooks

# Connect to ServiceNow API
instance = ''
username = ''
password = ''

endpoint = '/api/now/table/incident'
user_endpoint = '/api/now/table/sys_user'

# Form the complete URL to find the user sys_id
user_name = 'System Administrator'
url = f"{instance}{user_endpoint}?sysparm_query=name={user_name}"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Get the sys_id for the caller
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
    url = f"{instance}{endpoint}?sysparm_query={filter_query}"

    try:
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
        response.raise_for_status()
        data = response.json()

        if data['result']:
            for incident in data['result']:
                incident_description = incident.get('short_description', 'default')
                print(f"Incident Description: {incident_description}")

                # Search for playbooks related to the incident description
                print("Searching for playbooks related to the incident description...")
                matching_playbooks = search_playbook_contents('./existing_playbooks', incident_description)

                if matching_playbooks:
                    for match in matching_playbooks:
                        print(f"Found in file: {match['file']}")
                        if 'task' in match:
                            print(f"Task: {match['task']}")
                else:
                    print("No matching playbooks found.")
        else:
            print("No incidents found.")
    except Exception as e:
        print(f"An error occurred when querying incidents: {e}")
else:
    print("Cannot proceed without a valid sys_id")

# # Generate a new playbook if no matching playbooks were found
# if not matching_playbooks:
#     print("No matching playbooks found. Generating a new playbook...")
#     try:
#         completion = client.chat.completions.create(model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant."},
#             {
#                 "role": "user",
#                 "content": "Write an Ansible playbook that prints 'Hello Ansible World'."
#             }
#         ])

#         # Print the generated playbook
#         generated_playbook = completion.choices[0].message.content
#         print("Generated Playbook:")
#         print(generated_playbook)

#         # Optionally, save the generated playbook to a file
#         with open('./existing_playbooks/generated_playbook.yml', 'w') as file:
#             file.write(generated_playbook)
#             print("Generated playbook saved as 'generated_playbook.yml'.")
#     except Exception as e:
#         print(f"An error occurred while generating the playbook: {e}")
