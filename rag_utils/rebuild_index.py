import sys
from pathlib import Path

# Access parent directory
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from llama_interface import create_faiss_index

if __name__ == "__main__":
    print("Rebuilding FAISS index...")
    create_faiss_index(use_gpu=False)
    print("FAISS index rebuilt successfully.")
