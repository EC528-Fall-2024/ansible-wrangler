from llama_interface import load_retrieval_system, retrieve_playbooks

if __name__ == "__main__":
    # Load the FAISS index and documents
    load_retrieval_system(use_gpu=False)  # Adjust GPU usage based on your setup

    # Test retrieval for a specific query
    query = "Deploy Apache on webservers"
    playbooks = retrieve_playbooks(query, top_k=3, use_gpu=False)

    print("\nRetrieved Playbooks:")
    for idx, playbook in enumerate(playbooks, 1):
        print(f"Playbook {idx}:\n{playbook}\n")
