import os
import requests

def search_ansible_playbooks(query="ansible playbook", language="yaml", per_page=10, download_folder="ansible_playbooks"):
    # GitHub API endpoint for searching repositories
    url = "https://api.github.com/search/code"
    
    # Parameters for the search query
    params = {
        "q": f"{query} language:{language}",
        "per_page": per_page,
        "sort": "stars",
        "order": "desc"
    }
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "token TOKEN"  # Replace with your GitHub token
    }
    
    # Create the download folder if it doesn't exist
    os.makedirs(download_folder, exist_ok=True)
    
    # Perform the API request
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        results = response.json()["items"]
        for item in results:
            file_url = item["html_url"].replace("github.com", "raw.githubusercontent.com").replace("/blob", "")
            file_name = f"{item['repository']['name']}_{item['path'].replace('/', '_')}"
            file_path = os.path.join(download_folder, file_name)

            # Download and save each YAML file
            file_response = requests.get(file_url)
            if file_response.status_code == 200:
                with open(file_path, "w") as file:
                    file.write(file_response.text)
                print(f"Downloaded {file_name}")
            else:
                print(f"Failed to download {file_name}, Status code: {file_response.status_code}")
    else:
        print(f"Failed to retrieve results. Status code: {response.status_code}, Message: {response.json().get('message')}")

# Run the search and download function
search_ansible_playbooks()