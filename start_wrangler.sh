#!/bin/bash

# Check if Conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda is not installed. Installing Miniconda..."

    # Download Miniconda installer
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O conda.sh

    # Run the installer in batch mode
    bash conda.sh -b -p ~/local/miniconda3

    # Clean up the installer
    rm -f conda.sh

    # Initialize Conda for bash
    ~/local/miniconda3/bin/conda init bash

    # Ask the user to rerun the script after sourcing
    echo "Conda has been installed. Please restart your terminal or run 'source ~/.bashrc' and then execute this script again to complete the setup."
    exit 0
else
    echo "Conda is already installed."
fi

# Ensure the script is running with Conda initialized
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Conda is initialized. Proceeding with environment setup..."
else
    echo "Conda environment detected: $CONDA_DEFAULT_ENV"
fi

# Check if the 'faiss_env' environment exists
if conda env list | grep -q 'faiss_env'; then
    echo "Conda environment 'faiss_env' already exists."
else
    echo "Creating Conda environment 'faiss_env'..."
    conda create -n faiss_env python=3.9 -y
    echo "Conda environment 'faiss_env' created."
fi

# Activate the 'faiss_env' environment
echo "Activating Conda environment 'faiss_env'..."
source ~/local/miniconda3/bin/activate faiss_env

# Check if `main.py` exists in the current directory
if [ -f "main.py" ]; then
    echo "Running 'main.py'..."
    python3 main.py
else
    echo "'main.py' not found in the current directory. Please ensure it exists and rerun this script."
fi
