import requests
import base64

def upload_new_playbook_to_repo(branch_name, file_path, playbook_content, GITHUB_API_URL, github_token):

  headers = {'Authorization': f'token {github_token}'}

  # Encode the playbook content in base64 (as required by GitHub API)
  encoded_content = base64.b64encode(playbook_content.encode()).decode()

  # Prepare the payload for the API request
  data = {
      "message": f"Add new playbook: {file_path}",
      "content": encoded_content,
      "branch": branch_name
  }

  # Construct the URL to upload the file to the repo
  file_url = f"{GITHUB_API_URL}/contents/{file_path}"
  response = requests.put(file_url, headers=headers, json=data)

  # Check the response from the GitHub API
  if response.status_code in [200, 201]:
      print(f"New playbook {file_path} added successfully to {branch_name}.")
  else:
      raise Exception(f"Error uploading playbook: {response.status_code}, {response.text}")