#!/bin/bash

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to install packages on Ubuntu
install_ubuntu_dependencies() {
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip python3-opencv
}

# Function to install MacOS-specific dependencies inside the virtual environment
install_macos_dependencies() {
  pip install pyobjc
}

# Detect the operating system
os_type=$(uname)

# Check if Python is installed and install if necessary
if ! command_exists python3; then
  if [ "$os_type" = "Linux" ]; then
    install_ubuntu_dependencies
  elif [ "$os_type" = "Darwin" ]; then
    if ! command_exists brew; then
      echo "Homebrew is not installed. Please install Homebrew first."
      exit 1
    fi
    brew install python
  else
    echo "Unsupported operating system: $os_type"
    exit 1
  fi
fi

# Create a virtual environment
python3 -m venv oa-env

# Activate the virtual environment
source "oa-env/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install required packages from requirements.txt
pip install -r requirements.txt

# Install MacOS-specific dependencies inside the virtual environment
if [ "$os_type" = "Darwin" ]; then
  install_macos_dependencies
fi

# Deactivate the virtual environment
deactivate

echo -e "\n\n#############################################################"
echo -e "Setup complete. To activate the virtual environment, run:"
echo -e "./venv.sh on"
echo -e "#############################################################\n\n"
