#!/usr/bin/env python3
"""
Retrieval-Augmented Generation (RAG) System for Ansible Playbooks

This script integrates FAISS-GPU for retrieving existing Ansible playbooks
and LLaMA via Ollama for generating new playbooks when no suitable match is found.

Usage:
    - To index playbooks:
        python rag_system.py index
    - To query/generate a playbook:
        python rag_system.py query "Deploy a web server using Nginx on Ubuntu."
    - To evaluate existing playbooks against a description:
        python rag_system.py evaluate "Incident description." "path/to/playbook1.yml" "path/to/playbook2.yml"
"""

import os
import re
import subprocess
import sys
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ----------------------------
# Configuration Constants
# ----------------------------

PLAYBOOKS_DIR = 'existing_playbooks/'         # Directory containing existing playbooks
FAISS_INDEX_PATH = 'faiss.index'     # Path to save/load the FAISS index
DOCUMENTS_PATH = 'documents.txt'     # Path to save/load playbook contents
MODEL_NAME = 'llama3.2:1b'           # Ollama model name
TOP_K = 3                            # Number of top playbooks to retrieve

# ----------------------------
# Utility Functions
# ----------------------------

def create_faiss_index(use_gpu=True):
    """
    Create a FAISS index from existing Ansible playbooks, using GPU or CPU based on the 'use_gpu' argument.
    
    Args:
        use_gpu (bool): Whether to use GPU for FAISS indexing. Defaults to True.
    """
    print("Initializing embedding model...")
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model initialized successfully.")
    except Exception as e:
        print("Error initializing embedding model:", e)
        return

    # Verify playbooks directory
    if not os.path.exists(PLAYBOOKS_DIR):
        print(f"Playbooks directory '{PLAYBOOKS_DIR}' does not exist. Please create it and add playbook files.")
        return

    # Read and embed playbooks
    playbook_contents = []
    print(f"Reading playbooks from '{PLAYBOOKS_DIR}'...")
    for filename in os.listdir(PLAYBOOKS_DIR):
        if filename.endswith(('.yml', '.yaml')):
            filepath = os.path.join(PLAYBOOKS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    playbook_contents.append(content)
                    print(f"Read playbook: {filename}")
            except Exception as e:
                print(f"Error reading file '{filename}':", e)
    if not playbook_contents:
        print(f"No playbooks found in '{PLAYBOOKS_DIR}'. Please add `.yml` or `.yaml` files.")
        return

    print("Generating embeddings for playbooks...")
    try:
        embeddings = embedding_model.encode(playbook_contents, convert_to_numpy=True)
        embeddings = embeddings.astype('float32')  # FAISS requires float32
        print("Embeddings generated successfully.")
    except Exception as e:
        print("Error generating embeddings:", e)
        return

    dimension = embeddings.shape[1]
    print(f"Embedding dimension: {dimension}")

    # Create and populate FAISS index
    if use_gpu:
        print("Creating FAISS GPU index...")
        try:
            index_cpu = faiss.IndexFlatL2(dimension)  # Start with a CPU index
            gpu_res = faiss.StandardGpuResources()
            index_gpu = faiss.index_cpu_to_gpu(gpu_res, 0, index_cpu)
            index_gpu.add(embeddings)
            print("FAISS GPU index created and embeddings added successfully.")
        except Exception as e:
            print("Error creating or populating FAISS GPU index:", e)
            return

        print("Transferring GPU index back to CPU for saving...")
        try:
            index_cpu = faiss.index_gpu_to_cpu(index_gpu)
            print("FAISS index transferred back to CPU successfully.")
        except Exception as e:
            print("Error transferring FAISS GPU index back to CPU:", e)
            return
    else:
        print("Creating FAISS CPU index...")
        try:
            index_cpu = faiss.IndexFlatL2(dimension)
            index_cpu.add(embeddings)
            print("FAISS CPU index created and embeddings added successfully.")
        except Exception as e:
            print("Error creating or populating FAISS CPU index:", e)
            return

    # Save the FAISS index and playbook contents
    print(f"Saving FAISS index to '{FAISS_INDEX_PATH}'...")
    try:
        faiss.write_index(index_cpu, FAISS_INDEX_PATH)
        print("FAISS index saved successfully.")
    except Exception as e:
        print("Error saving FAISS index:", e)
        return

    print(f"Saving playbook contents to '{DOCUMENTS_PATH}'...")
    try:
        with open(DOCUMENTS_PATH, 'w', encoding='utf-8') as f:
            for doc in playbook_contents:
                # Each playbook on a single line
                f.write(doc.replace('\n', ' ') + '\n')
        print("Playbook contents saved successfully.")
    except Exception as e:
        print("Error saving playbook contents:", e)
        return

    print("Indexing completed successfully.")

def load_retrieval_system(use_gpu=True):
    """
    Load the FAISS index and playbook documents.
    Args:
        use_gpu (bool): Whether to load the FAISS index onto GPU. Defaults to True.

    Returns:
        index (faiss.Index): FAISS index on the specified device (CPU or GPU).
        documents (List[str]): List of playbook contents.
    """
    if not os.path.exists(FAISS_INDEX_PATH):
        print(f"FAISS index file '{FAISS_INDEX_PATH}' not found. Please run the indexing step first using the 'index' command.")
        sys.exit(1)

    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Documents file '{DOCUMENTS_PATH}' not found. Please run the indexing step first using the 'index' command.")
        sys.exit(1)

    print("Loading FAISS index from file...")
    try:
        index_cpu = faiss.read_index(FAISS_INDEX_PATH)
        print("FAISS index loaded from file successfully.")
    except Exception as e:
        print("Error loading FAISS index:", e)
        sys.exit(1)

    # Optionally transfer to GPU
    if use_gpu:
        print("Transferring FAISS index to GPU...")
        try:
            gpu_res = faiss.StandardGpuResources()
            index_gpu = faiss.index_cpu_to_gpu(gpu_res, 0, index_cpu)
            print("FAISS index transferred to GPU successfully.")
            index = index_gpu
        except Exception as e:
            print("Error transferring FAISS index to GPU:", e)
            sys.exit(1)
    else:
        print("Using FAISS index on CPU...")
        index = index_cpu

    print(f"Loading playbook contents from '{DOCUMENTS_PATH}'...")
    try:
        with open(DOCUMENTS_PATH, 'r', encoding='utf-8') as f:
            documents = [line.strip() for line in f]
        print("Playbook contents loaded successfully.")
    except Exception as e:
        print("Error loading playbook contents:", e)
        sys.exit(1)

    print("Retrieval system loaded successfully.")
    return index, documents

def retrieve_playbooks(query, top_k=TOP_K, use_gpu=True):
    """
    Retrieve the top_k most relevant playbooks based on the query.
    Args:
        query (str): The input task or incident description.
        top_k (int): Number of top documents to retrieve.
    Returns:
        List[str]: A list of retrieved playbook contents.
    """
    print("Initializing embedding model for retrieval...")
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model initialized successfully.")
    except Exception as e:
        print("Error initializing embedding model:", e)
        return []

    print("Generating embedding for the query...")
    try:
        query_embedding = embedding_model.encode([query]).astype('float32')
        print("Query embedding generated successfully.")
    except Exception as e:
        print("Error generating query embedding:", e)
        return []

    print("Performing similarity search...")
    try:
        if use_gpu:
            distances, indices = index_gpu.search(query_embedding, top_k)
        else:
            distances, indices = index_cpu.search(query_embedding, top_k)
        print("Similarity search completed.")
    except Exception as e:
        print("Error during similarity search:", e)
        return []

    retrieved = []
    for idx in indices[0]:
        if idx < len(documents):
            retrieved.append(documents[idx])
        else:
            retrieved.append("Invalid index retrieved.")
    print(f"Retrieved {len(retrieved)} playbooks.")
    return retrieved

def prune_ansible_playbook(response):
    """
    Extract and return the Ansible playbook from the response.
    Args:
        response (dict): The response dictionary from Ollama.
    Returns:
        str: The pruned Ansible playbook or an error message.
    """
    if isinstance(response, dict):
        if 'content' in response:
            response_message = response['content']
            if not isinstance(response_message, str):
                print(f"Expected 'content' to be a string, but got {type(response_message)}.")
                return "Invalid response format."
        else:
            print("'content' key not found in the response.")
            return "Invalid response format."
    else:
        print(f"Expected a dictionary from the API, but got {type(response)}.")
        return "Invalid response format."

    # Extract code blocks enclosed in ```
    code_block_match = re.search(r'```([\s\S]+?)```', response_message)

    if code_block_match:
        code_block = code_block_match.group(1)
        # Extract YAML playbook starting with ---
        playbook_match = re.search(r'---[\s\S]+?(?:\n\.\.\.|$)', code_block)
        if playbook_match:
            return playbook_match.group(0)
        else:
            print("No valid Ansible playbook found within the code block.")
            return "No valid Ansible playbook found within the code block."
    else:
        print("No code block found in the response.")
        return "No code block found in the response."

def query_llama(prompt, model_name=MODEL_NAME):
    """
    Query the LLaMA model via Ollama with the given prompt.
    Args:
        prompt (str): The prompt to send to the model.
        model_name (str): The name of the model in Ollama.
    Returns:
        str or None: The response from the model or None if an error occurred.
    """
    command = ['ollama', 'run', model_name, prompt]
    try:
        print(f"Querying LLaMA model '{model_name}'...")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        response = result.stdout.strip()
        print("Received response from LLaMA.")
        return response
    except subprocess.CalledProcessError as e:
        print("Error querying LLaMA:", e.stderr)
        return None

def generate_ansible_playbook(task_description, use_gpu=True):
    """
    Generate an Ansible playbook for the given task description.
    Attempts to retrieve a matching playbook first; generates one if none found.
    Args:
        task_description (str): Description of the task for which to create the playbook.
    Returns:
        str: The generated or retrieved Ansible playbook.
    """
    print(f"Generating playbook for task: {task_description}")
    retrieved_playbooks = retrieve_playbooks(task_description, use_gpu=use_gpu)

    if retrieved_playbooks and any(pb.strip() for pb in retrieved_playbooks):
        print("Retrieved Playbooks:")
        for idx, pb in enumerate(retrieved_playbooks, 1):
            print(f"Playbook {idx}:\n{pb}\n")
        return retrieved_playbooks[0]#"Relevant playbooks were found. Please review the retrieved playbooks."
    else:
        print("No relevant playbooks found. Proceeding to generate a new playbook.")
        prompt = f"Write a single Ansible playbook for the following task: {task_description}. Don't explain anything, I just want a solid playbook."
        response_content = query_llama(prompt)
        if response_content:
            playbook = prune_ansible_playbook({'content': response_content})
            return playbook
        else:
            return "Failed to generate playbook."
    

def evaluate_playbooks_with_llama(existing_playbooks, description, use_gpu=True):
    """
    Evaluate existing playbooks against an incident description.
    Attempts to retrieve relevant playbooks first; generates one if no match is found.
    Args:
        existing_playbooks (List[str]): List of existing Ansible playbook contents.
        description (str): Description of the incident to match against playbooks.
    Returns:
        str: The matching playbook if found, else a newly generated playbook.
    """
    print(f"Evaluating playbooks for incident: {description}")
    retrieved_playbooks = retrieve_playbooks(description, use_gpu=use_gpu)

    if retrieved_playbooks and any(pb.strip() for pb in retrieved_playbooks):
        print("Retrieved Playbooks for Evaluation:")
        for idx, pb in enumerate(retrieved_playbooks, 1):
            print(f"Retrieved Playbook {idx}:\n{pb}\n")
    else:
        print("No relevant playbooks retrieved for evaluation.")

    # Evaluate each existing playbook
    for idx, playbook in enumerate(existing_playbooks, 1):
        print(f"Evaluating Playbook {idx}...")
        prompt = f"""
You are an expert in Ansible playbooks. Evaluate if the provided playbook content matches the given incident description. Just say "IT MATCHES" in case of match and "IT DOES NOT MATCH" otherwise.
Incident description: {description}
Playbook content: {playbook}
"""
        response_content = query_llama(prompt)
        if response_content:
            evaluation = response_content.strip().upper()
            print(f"Evaluation Response: {evaluation}")
            if "IT MATCHES" in evaluation:
                print("A matching playbook has been found.")
                return playbook
        else:
            print("Failed to get evaluation from LLaMA.")

    print("No matching playbook found. Generating a new playbook.")
    generated_playbook = generate_ansible_playbook(description)
    return generated_playbook

# ----------------------------
# Main Execution Logic
# ----------------------------

def main(use_gpu=True):
    """
    Main function to handle indexing, querying, and evaluating playbooks.
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("  To index playbooks:")
        print("    python rag_system.py index")
        print("  To query/generate a playbook:")
        print('    python rag_system.py query "Deploy a web server using Nginx on Ubuntu."')
        print('  To evaluate existing playbooks:')
        print('    python rag_system.py evaluate "Incident description." "path/to/playbook1.yml" "path/to/playbook2.yml"')
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'index':
        create_faiss_index(use_gpu=use_gpu)
    elif command == 'query':
        if len(sys.argv) < 3:
            print("Please provide a task description for querying.")
            print('Example: python rag_system.py query "Deploy a web server using Nginx on Ubuntu."')
            sys.exit(1)
        task_description = sys.argv[2]
        playbook = generate_ansible_playbook(task_description, use_gpu=use_gpu)
        print("\n--- Generated/ Retrieved Ansible Playbook ---")
        print(playbook)
    elif command == 'evaluate':
        if len(sys.argv) < 4:
            print("Please provide an incident description and at least one playbook file path for evaluation.")
            print('Example: python rag_system.py evaluate "Incident description." "playbook1.yml" "playbook2.yml"')
            sys.exit(1)
        description = sys.argv[2]
        playbook_files = sys.argv[3:]
        existing_playbooks = []
        for filepath in playbook_files:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_playbooks.append(f.read())
                        print(f"Loaded playbook from '{filepath}'.")
                except Exception as e:
                    print(f"Error reading playbook '{filepath}':", e)
            else:
                print(f"Playbook file '{filepath}' does not exist. Skipping.")
        if not existing_playbooks:
            print("No valid playbook files provided for evaluation.")
            sys.exit(1)
        matching_playbook = evaluate_playbooks_with_llama(existing_playbooks, description, use_gpu=use_gpu)
        print("\n--- Matching Ansible Playbook ---")
        print(matching_playbook)
    else:
        print(f"Unknown command '{command}'.")
        print("Valid commands are: index, query, evaluate.")
        sys.exit(1)

# ----------------------------
# Entry Point
# ----------------------------

if __name__ == "__main__":
    # Load retrieval system globally
    use_gpu =False
    if len(sys.argv) >= 2 and sys.argv[1].lower() == 'index':
        # If indexing, do not load retrieval system
        pass
    else:
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCUMENTS_PATH):
            print("Loading retrieval system...")
            if use_gpu:
                index_gpu, documents = load_retrieval_system(use_gpu=use_gpu)
            else:
                index_cpu, documents = load_retrieval_system(use_gpu=use_gpu)
        else:
            print("FAISS index or documents not found. Please run the indexing step first using the 'index' command.")
            sys.exit(1)
    main(use_gpu=use_gpu)
