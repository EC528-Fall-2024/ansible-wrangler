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

# Create the Conda environment from environment.yml if it exists
if [ -f "environment.yml" ]; then
    echo "Creating Conda environment from environment.yml..."
    conda env create -f environment.yml
else
    echo "No environment.yml found, skipping Conda environment creation."
fi

# Activate the Conda environment
echo "Activating Conda environment 'faiss_env'..."
conda activate faiss_env

# Run main.py
echo "Running main.py..."
python main.py
