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

PLAYBOOKS_DIR = 'existing_playbooks/'        # Directory containing existing playbooks
FAISS_INDEX_PATH = 'faiss.index'             # Path to save/load the FAISS index
DOCUMENTS_PATH = 'documents.txt'             # Path to save/load playbook contents
MODEL_NAME = 'qwen2.5-coder:32b'             # Ollama model name
TOP_K = 3                                    # Number of top playbooks to retrieve

index_gpu = None
index_cpu = None
documents = []

# ----------------------------
# Utility Functions
# ----------------------------

def create_faiss_index(use_gpu=True):
    """
    Create a FAISS index from existing Ansible playbooks, ensuring consistency between playbooks and embeddings.
    """
    print("Initializing embedding model...")
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model initialized successfully.")
    except Exception as e:
        print(f"Error initializing embedding model: {e}")
        return

    if not os.path.exists(PLAYBOOKS_DIR):
        print(f"Playbooks directory '{PLAYBOOKS_DIR}' does not exist. Please create it and add playbook files.")
        return

    playbook_contents = []
    formatted_playbooks = []
    print(f"Reading playbooks from directory: {PLAYBOOKS_DIR}")
    for filename in os.listdir(PLAYBOOKS_DIR):
        if filename.endswith(('.yml', '.yaml')):
            filepath = os.path.join(PLAYBOOKS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    playbook_contents.append(content.replace("\n", " "))
                    formatted_playbooks.append(content.strip())
                    print(f"Successfully read playbook: {filename}")
            except Exception as e:
                print(f"Error reading playbook '{filename}': {e}")

    if not playbook_contents:
        print(f"No playbooks found in '{PLAYBOOKS_DIR}'. Please add `.yml` or `.yaml` files.")
        return

    print(f"Total playbooks read: {len(playbook_contents)}")

    try:
        print("Generating embeddings for playbooks...")
        embeddings = embedding_model.encode(playbook_contents, convert_to_numpy=True).astype('float32')
        print(f"Embeddings generated successfully. Total embeddings: {embeddings.shape[0]}")
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return

    if len(playbook_contents) != embeddings.shape[0]:
        print("Error: Mismatch between playbook contents and generated embeddings.")
        return

    dimension = embeddings.shape[1]
    print(f"Embedding dimension: {dimension}")
    try:
        print("Creating FAISS index...")
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        print("FAISS index created and embeddings added successfully.")
    except Exception as e:
        print(f"Error creating or populating FAISS index: {e}")
        return

    try:
        print(f"Saving FAISS index to '{FAISS_INDEX_PATH}'...")
        faiss.write_index(index, FAISS_INDEX_PATH)
        print("FAISS index saved successfully.")
    except Exception as e:
        print(f"Error saving FAISS index: {e}")
        return

    try:
        print(f"Saving formatted playbooks to '{DOCUMENTS_PATH}'...")
        with open(DOCUMENTS_PATH, 'w', encoding='utf-8') as f:
            for doc in formatted_playbooks:
                f.write(f"{doc}\n---END---\n")
        print("Formatted playbooks saved successfully.")
    except Exception as e:
        print(f"Error saving formatted playbooks: {e}")
        return

    print("Indexing completed successfully.")

def load_retrieval_system(use_gpu=True):
    """
    Load the FAISS index and playbook documents.
    """
    global index_gpu, index_cpu, documents

    if not os.path.exists(FAISS_INDEX_PATH):
        print(f"FAISS index file '{FAISS_INDEX_PATH}' not found. Please run the indexing step first.")
        sys.exit(1)

    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Documents file '{DOCUMENTS_PATH}' not found. Please run the indexing step first.")
        sys.exit(1)

    print("Loading FAISS index from file...")
    try:
        index_cpu = faiss.read_index(FAISS_INDEX_PATH)
        print("FAISS index loaded from file successfully.")
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        sys.exit(1)

    if use_gpu:
        print("Transferring FAISS index to GPU...")
        try:
            gpu_res = faiss.StandardGpuResources()
            index_gpu = faiss.index_cpu_to_gpu(gpu_res, 0, index_cpu)
            print("FAISS index transferred to GPU successfully.")
        except Exception as e:
            print(f"Error transferring FAISS index to GPU: {e}")
            index_gpu = None
    else:
        index_gpu = None

    print(f"Loading playbook contents from '{DOCUMENTS_PATH}'...")
    try:
        with open(DOCUMENTS_PATH, 'r', encoding='utf-8') as f:
            documents = [line.strip() for line in f]
        print("Playbook contents loaded successfully.")
    except Exception as e:
        print(f"Error loading playbook contents: {e}")
        sys.exit(1)

    print("Retrieval system loaded successfully.")

def retrieve_playbooks(query, top_k=TOP_K, use_gpu=True):
    """
    Retrieve the top_k most relevant playbooks based on the query.
    """
    global index_gpu, index_cpu

    print("Initializing embedding model for retrieval...")
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model initialized successfully.")
    except Exception as e:
        print(f"Error initializing embedding model: {e}")
        return []

    print("Generating embedding for the query...")
    try:
        query_embedding = embedding_model.encode([query]).astype('float32')
        print("Query embedding generated successfully.")
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return []

    print("Performing similarity search...")
    try:
        index = index_gpu if use_gpu else index_cpu
        if index is None:
            raise ValueError("FAISS index is not loaded.")
        distances, indices = index.search(query_embedding, top_k)
        print(f"Retrieved indices: {indices}")
        print(f"Distances: {distances}")
    except Exception as e:
        print(f"Error during similarity search: {e}")
        return []

    try:
        with open(DOCUMENTS_PATH, 'r', encoding='utf-8') as f:
            all_playbooks = f.read().split("\n---END---\n")
        print(f"Total playbooks loaded: {len(all_playbooks)}")
    except Exception as e:
        print(f"Error loading playbooks: {e}")
        return []

    retrieved = []
    for idx in indices[0]:
        if 0 <= idx < len(all_playbooks):
            retrieved.append(all_playbooks[idx].strip())
        else:
            print(f"Invalid index retrieved: {idx}")
    print(f"Retrieved {len(retrieved)} playbooks.")
    return retrieved

def prune_ansible_playbook(response):
    """
    Extract and return the Ansible playbook from the response.
    """
    if isinstance(response, dict):
        response_message = response.get('content', '')
        if not isinstance(response_message, str):
            print(f"Expected 'content' to be a string, but got {type(response_message)}.")
            return "Invalid response format."
    else:
        print(f"Expected a dictionary, but got {type(response)}.")
        return "Invalid response format."

    code_block_match = re.search(r'```([\s\S]+?)```', response_message)
    if code_block_match:
        code_block = code_block_match.group(1)
        playbook_match = re.search(r'---[\s\S]+?(?:\n\.\.\.|$)', code_block)
        return playbook_match.group(0) if playbook_match else "No valid playbook found."
    return "No code block found."

def query_llama(prompt, model_name=MODEL_NAME):
    """
    Query the LLaMA model via Ollama with the given prompt.
    """
    command = ['ollama', 'run', model_name, prompt]
    try:
        print(f"Querying LLaMA model '{model_name}'...")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("Received response from LLaMA.")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error querying LLaMA: {e.stderr}")
        return None

def generate_ansible_playbook(task_description, regenerate_with_ai=False, use_gpu=True):
    """
    Generate an Ansible playbook for the given task description.
    """
    if regenerate_with_ai:
        print("Strict AI generation requested.")
        prompt = f"Write a single Ansible playbook for the following task: {task_description}. Don't explain anything, just return the playbook."
        response_content = query_llama(prompt)
        return prune_ansible_playbook({'content': response_content}) if response_content else "Failed to generate playbook."

    print("Attempting to retrieve playbooks...")
    retrieved_playbooks = retrieve_playbooks(task_description, use_gpu=use_gpu)
    if retrieved_playbooks:
        return retrieved_playbooks[0]

    print("No relevant playbooks found. Generating a new playbook.")
    prompt = f"Write a single Ansible playbook for the following task: {task_description}. Don't explain anything, just return the playbook."
    response_content = query_llama(prompt)
    return prune_ansible_playbook({'content': response_content}) if response_content else "Failed to generate playbook."
