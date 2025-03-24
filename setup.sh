#!/usr/bin/env bash

set -e

# Desired Python version
PYTHON_VERSION="3.12.8"

# Function to display usage information
display_usage() {
    cat <<EOF
Usage: ./setup.sh [OPTIONS]

This script sets up the oaTracker environment, including Python and required dependencies.

Options:
  -h, --help              Display this help message and exit
  -c, --clean             Clean up previous installations before setup
  -p, --pyenv <option>    Specify pyenv installation option:
                            skip    - Skip pyenv installation/update (default)
                            update  - Update existing pyenv installation
                            force   - Force a fresh pyenv installation
  --force                 Equivalent to --pyenv force

Examples:
  ./setup.sh                      # Run setup with default options
  ./setup.sh --clean              # Clean up and run setup

Note:
  - This script supports both macOS and Ubuntu.
  - It will install Homebrew on macOS if not already installed.
  - The script creates a Python virtual environment named '.venv'.
  - After running the script, activate the virtual environment with:
    source .venv/bin/activate         (for bash/zsh)
    source .venv/bin/activate.fish    (for fish shell)

EOF
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the current shell
detect_shell() {
    THE_SHELL=$(basename "$SHELL")

    if [ "$THE_SHELL" == "fish" ]; then
        echo "fish"
    elif [ "$THE_SHELL" == "zsh" ]; then
        echo "zsh"
    elif [ "$THE_SHELL" == "bash" ]; then
        echo "bash"
    else
        echo "unknown"
    fi
}

# Function to install packages on Ubuntu
install_ubuntu_dependencies() {
    echo "Updating package lists..."
    sudo apt-get update
    echo "Installing build dependencies..."
    sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
        libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
        xz-utils tk-dev libffi-dev liblzma-dev python3-opencv;
}

install_uv() {
    if ! command -v uv 2>&1 >/dev/null
    then
        echo "uv could not be found"
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
}

# Function to install packages on macOS
install_macos_dependencies() {
    if ! command_exists brew; then
        echo "Homebrew is not installed. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "Updating Homebrew..."
        brew update
    fi
    echo "Checking and installing build dependencies..."

    for pkg in openssl@3 readline sqlite xz zlib; do
        if brew list --versions $pkg >/dev/null; then
            echo "$pkg is already installed"
        else
            echo "Installing $pkg"
            brew install $pkg
        fi
    done
}

# Function to install Python using pyenv
install_python() {
    uv python install $PYTHON_VERSION
}

# Function to set up Python virtual environment
setup_venv() {
    # Activate virtual environment based on shell
    uv venv .venv --python $PYTHON_VERSION
    source .venv/bin/activate

    echo "Installing required packages..."
    uv pip install -r pyproject.toml
}

# Function to clean up previous installations
cleanup() {
    echo "Cleaning up previous installations..."
    rm -rf .venv || true
    rm -rf "$PYENV_ROOT" || true
    echo "Cleanup complete."
}

# Parse command-line arguments
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
        display_usage
        exit 0
        ;;
    -c | --clean)
        CLEAN=true
        shift
        ;;
    esac
done

# Detect the operating system
OS_TYPE=$(uname)

# Detect the shell
DETECTED_SHELL=$(detect_shell)

echo "Detected OS: $OS_TYPE"
echo "Detected shell: $DETECTED_SHELL"

# Perform cleanup if requested
if $CLEAN; then
    cleanup
fi

install_uv

# Install OS-specific dependencies
if [ "$OS_TYPE" = "Linux" ]; then
    install_ubuntu_dependencies
elif [ "$OS_TYPE" = "Darwin" ]; then
    install_macos_dependencies
else
    echo "Unsupported operating system: $OS_TYPE"
    exit 1
fi

# # Install desired Python version
install_python

# # Set up virtual environment and install dependencies
setup_venv

sudo rm -rf vidformer || true;
git clone https://github.com/ixlab/vidformer
cd vidformer
docker build -t igni -f Dockerfile .

# Deactivate the virtual environment
deactivate

echo -e "\n\n#############################################################"
echo -e "Setup complete. To activate the virtual environment, run:"
echo -e "source .venv/bin/activate"
if [ "$DETECTED_SHELL" = "fish" ]; then
    echo -e "For fish shell, use: source .venv/bin/activate.fish"
fi
echo -e "#############################################################\n\n"
