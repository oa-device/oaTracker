#!/bin/bash

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
	echo "Python3 could not be found, please install it first."
	exit
fi

# Create a virtual environment
python3 -m venv oaTracker-env

# Activate the virtual environment
source oaTracker-env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages from requirements.txt
pip install -r requirements.txt

# Save the installed packages to requirements.txt
# pip freeze >requirements.txt

# Deactivate the virtual environment
# deactivate

# To activate the virtual environment
# source oaTracker-env/bin/activate
# source oaTracker-env/bin/activate.fish
