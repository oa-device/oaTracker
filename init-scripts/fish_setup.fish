#!/usr/bin/env fish

# Function to check if a command exists
function command_exists
    command -v $argv >/dev/null 2>&1
end

# Function to install packages on Ubuntu
function install_ubuntu_dependencies
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip python3-opencv
end

# Function to install packages on MacOS
function install_macos_dependencies
    if not command_exists brew
        echo "Homebrew is not installed. Please install Homebrew first."
        exit 1
    end
    brew install python
end

# Detect the operating system
set os_type (uname)

# Check if Python is installed and install if necessary
if not command_exists python3
    if test "$os_type" = "Linux"
        install_ubuntu_dependencies
    else if test "$os_type" = "Darwin"
        install_macos_dependencies
    else
        echo "Unsupported operating system: $os_type"
        exit 1
    end
end

# Create a virtual environment
python3 -m venv oa-env

# Activate the virtual environment
source "oa-env/bin/activate.fish"

# Upgrade pip
pip install --upgrade pip

# Install required packages from requirements.txt
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate

echo -e "\n\n#############################################################"
echo -e "Setup complete. To activate the virtual environment in Fish shell, run:"
echo -e "source oa-env/bin/activate.fish"
echo -e "#############################################################\n\n"
