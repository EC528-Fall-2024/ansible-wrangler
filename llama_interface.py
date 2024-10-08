import ollama
import re

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