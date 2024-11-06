import ollama
import re
import requests

ollama_client = ollama.Client('http://localhost:11434')


def prune_ansible_playbook(response):
    # Check if the response is in the expected format (string)
    if isinstance(response, dict):
        print("Response is a dictionary, keys are:", response.keys())
        
        # Check if 'message' is present in the response and is a string
        if 'content' in response:
            response_message = response['content']
            if not isinstance(response_message, str):
                raise TypeError(f"Expected 'message' to be a string, but got {type(response_message)}.")
        else:
            raise KeyError("'message' key not found in the response.")
    else:
        raise TypeError(f"Expected a dictionary from the API, but got {type(response)}.")

    # Log the message part for debugging
    print("Full message from the response:\n", response_message)

    # Now apply the regex on the message string to prune the playbook content
    code_block_match = re.search(r'```([\s\S]+?)```', response_message)

    if code_block_match:
        # Extract the content between the backticks
        code_block = code_block_match.group(1)
        print("Code block found:\n", code_block)
        
        # Now, search for the YAML playbook part starting with '---'
        playbook_match = re.search(r'---[\s\S]+?(?:\n\.\.\.|$)', code_block)

        if playbook_match:
            # Return only the playbook portion
            return playbook_match.group(0)
        else:
            return "No valid Ansible playbook found within the code block."
    else:
        return "No code block found."

def generate_ansible_playbook(task_description):
    model_name = "llama3.2:1b"

    prompt = f"Write a single Ansible playbook for the following task: {task_description}. Don't explain anything, I just want solid playbook."

    # Getting response from the ollama chat model
    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    # Prune the response to only maintain the playbook
    return prune_ansible_playbook(response['message'])


def evaluate_playbooks_with_llama(git_repo_url, branch, directory, description):
    # Remove the '.git' at the end if present
    if git_repo_url.endswith('.git'):
        git_repo_url = git_repo_url[:-4]

    # Split the URL by '/'
    parts = git_repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]

    # Construct the API URL to get the contents of the directory
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{directory}?ref={branch}'

    # Make the GET request to the API
    response = requests.get(api_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch contents from GitHub API. Status code: {response.status_code}")

    files = response.json()

    # Filter out files (ignore subdirectories)
    playbook_files = [file for file in files if file['type'] == 'file']

    # Loop through each playbook file
    for playbook_file in playbook_files:
        # Get the raw content of the playbook file
        download_url = playbook_file['download_url']
        playbook_response = requests.get(download_url)
        if playbook_response.status_code != 200:
            print(f"Failed to fetch playbook {playbook_file['name']}. Status code: {playbook_response.status_code}")
            continue

        playbook_content = playbook_response.text

        # Now evaluate the playbook as before
        prompt = f"""
        You are an expert in Ansible playbooks. Evaluate if the provided playbook content matches the given incident description. Just say "IT MATCHES" in case of match and "IT DOES NOT MATCH" otherwise.
        Incident description: {description}
        Playbook content: {playbook_content}
        """

       # Call LLaMA 3.2 1B via ollama
        response = ollama.chat(
            model="llama3.2:1b",
            messages=[{"role": "system", "content": prompt}]
        )


        # Extract the evaluation from the response
        print(response)
        evaluation = response['message']['content'].strip()

        # Check if the evaluation mentions that the playbook matches the incident
        if "IT MATCHES" in evaluation.upper():
            return playbook_content

    # Return None if no matching playbook is found
    return None

# # Example usage
# description = "Print message Hello Ansible World"
# git_repo_url = 'https://github.com/EC528-Fall-2024/ansible-wrangler.git'
# branch = 'Mac-New'
# directory = 'existing_playbooks'

# matching_playbook = evaluate_playbooks_with_llama(git_repo_url, branch, directory, description)

# if matching_playbook:
#     print("Matching playbook found:\n", matching_playbook)
# else:
#     print("No matching playbook found.")
    