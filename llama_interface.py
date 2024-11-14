import ollama
import re
import requests

# Initialize Ollama client
ollama_client = ollama.Client('http://localhost:11434')

def prune_ansible_playbook(response):
    """
    Extracts the playbook content from the response message.
    Args:
        response (dict): The response from the Ollama API containing the playbook content.
    Returns:
        str: The pruned playbook content or an error message if the playbook is not found.
    """
    # Validate response structure
    if not isinstance(response, dict) or 'content' not in response:
        raise ValueError("Invalid response format. Expected a dictionary with 'content' key.")
    
    response_message = response['content']

    # Extract content within code block and YAML section
    code_block_match = re.search(r'```([\s\S]+?)```', response_message)
    if code_block_match:
        code_block = code_block_match.group(1)
        
        playbook_match = re.search(r'---[\s\S]+?(?:\n\.\.\.|$)', code_block)
        if playbook_match:
            return playbook_match.group(0)
        else:
            return "No valid Ansible playbook found within the code block."
    else:
        return "No code block found."

def generate_ansible_playbook(task_description):
    """
    Generates an Ansible playbook based on a given task description.
    Args:
        task_description (str): The task description for which to generate the playbook.
    Returns:
        str: The generated Ansible playbook.
    """
    model_name = "llama3.2:1b"
    prompt = f"Write a single Ansible playbook for the following task: {task_description}. Only output the playbook, no explanations."

    # Call Ollama API
    response = ollama_client.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    return prune_ansible_playbook(response.get('message', {}))

def evaluate_playbooks_with_llama(git_repo_url, branch, directory, description):
    """
    Evaluates existing playbooks in a GitHub repository to find a match for a given description.
    Args:
        git_repo_url (str): The GitHub repository URL.
        branch (str): The branch name in the repository.
        directory (str): The directory containing playbooks.
        description (str): The incident description to evaluate against.
    Returns:
        str: The matching playbook content if found, otherwise None.
    """
    # Prepare GitHub API URL
    repo_api_url = git_repo_url.rstrip('/').replace('.git', '')
    owner, repo = repo_api_url.split('/')[-2:]
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{directory}?ref={branch}'

    # Fetch contents of the directory from GitHub API
    response = requests.get(api_url)
    response.raise_for_status()
    files = response.json()

    # Process each file in the directory
    for file in files:
        if file['type'] != 'file':
            continue

        # Download file content
        download_url = file['download_url']
        playbook_response = requests.get(download_url)
        playbook_response.raise_for_status()
        playbook_content = playbook_response.text

        # Generate evaluation prompt
        prompt = f"""
        You are an expert in Ansible playbooks. Evaluate if the provided playbook content matches the given incident description. 
        Output "CONFIRM MATCH" (all caps) if it matches, and "NO MATCH" (all caps) otherwise. 
        You are to ignore weather the `hosts` parameter has any effect on a match.

        You are only outputting "CONFIRM MATCH" or "NO MATCH" - nothing else.


        Incident description: {description}
        Playbook content: {playbook_content}
        """        
        # Call Ollama API to evaluate
        response = ollama_client.chat(
            model="llama3.2:1b",
            messages=[{"role": "system", "content": prompt}]
        )
        
        # Extract the evaluation result
        evaluation = response.get('message', {}).get('content', '').strip()
        # print(evaluation)

        # Check if the playbook matches
        if "CONFIRM MATCH" in evaluation.upper():
            print("Matching playbook found:\n", playbook_content)  # Print the playbook content directly
            return playbook_content

    print("No matching playbook found.")
    return None

# Test code
# if __name__ == "__main__":
#     # Sample test data
#     git_repo_url = 'https://github.com/EC528-Fall-2024/ansible-wrangler.git'
#     branch = 'Mac-New'
#     directory = 'existing_playbooks'
#     description = "Print message Hello Ansible World"

#     # Run evaluation
#     evaluate_playbooks_with_llama(git_repo_url, branch, directory, description)