import requests
import base64

# Define the repository and branch
REPO_OWNER = "EC528-Fall-2024"  # Your GitHub username
REPO_NAME = "ansible-wrangler"  # Your repository name
BRANCH_NAME = "pull_request"  # You want to add to the main branch
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

def upload_new_playbook_to_repo(branch_name, file_path, playbook_content, github_token):
    """
    Upload a new playbook file to the main branch of the repository.
    """
    headers = {'Authorization': f'token {github_token}'}

    encoded_content = base64.b64encode(playbook_content.encode()).decode()

    data = {
        "message": f"Add new playbook: {file_path}",
        "content": encoded_content,
        "branch": branch_name
    }

    file_url = f"{GITHUB_API_URL}/contents/{file_path}"
    response = requests.put(file_url, headers=headers, json=data)

    if response.status_code in [200, 201]:
        print(f"New playbook {file_path} added successfully to {branch_name}.")
    else:
        raise Exception(f"Error uploading playbook: {response.status_code}, {response.text}")

github_token = ""  # Replace with your actual GitHub token
file_path = "my_new_playbook.yaml"  # Specify where to add the playbook in the repo
playbook_content = """
---
- name: Sample Playbook for test pull request
  hosts: localhost
  tasks:
    - name: Ensure test service is running
      service:
        name: test
        state: started
"""  # Replace with your playbook content

# Call the function to upload the new playbook
upload_new_playbook_to_repo(BRANCH_NAME, file_path, playbook_content, github_token)
