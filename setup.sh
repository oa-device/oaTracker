#!/usr/bin/env bash

set -e

# Desired Python version
PYTHON_VERSION="3.10.11"

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
  ./setup.sh --pyenv update       # Update existing pyenv and run setup
  ./setup.sh --force              # Force fresh pyenv installation and run setup
  ./setup.sh --clean --force      # Clean up, force fresh pyenv installation, and run setup

Note:
  - This script supports both macOS and Ubuntu.
  - It will install Homebrew on macOS if not already installed.
  - The script creates a Python virtual environment named 'venv'.
  - After running the script, activate the virtual environment with:
    source venv/bin/activate         (for bash/zsh)
    source venv/bin/activate.fish    (for fish shell)

EOF
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the current shell
detect_shell() {
    if [ -n "$BASH_VERSION" ]; then
        echo "bash"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$FISH_VERSION" ]; then
        echo "fish"
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
        xz-utils tk-dev libffi-dev liblzma-dev python3-opencv
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

# Function to install and configure pyenv
install_pyenv() {
    PYENV_ROOT="$HOME/.pyenv"
    if [ ! -d "$PYENV_ROOT" ]; then
        echo "pyenv is not installed. Installing pyenv..."
        curl https://pyenv.run | bash
        configure_pyenv
    elif [ "$PYENV_INSTALL" = "force" ]; then
        echo "Forcing pyenv reinstallation..."
        rm -rf "$PYENV_ROOT"
        curl https://pyenv.run | bash
        configure_pyenv
    elif [ "$PYENV_INSTALL" = "update" ]; then
        echo "Updating existing pyenv installation..."
        if [ -d "$PYENV_ROOT/.git" ]; then
            (
                cd "$PYENV_ROOT"
                git pull
            )
        else
            echo "Existing pyenv installation is not a git repository. Skipping update."
        fi
    else
        echo "Existing pyenv installation found. Skipping installation."
        echo "To update or reinstall pyenv, use the -p update or -p force option."
    fi
}

# Function to configure pyenv in shell
configure_pyenv() {
    # Set up shell environment for pyenv
    case $DETECTED_SHELL in
    fish)
        echo "set -Ux PYENV_ROOT $PYENV_ROOT" >>~/.config/fish/config.fish
        echo "set -U fish_user_paths $PYENV_ROOT/bin $fish_user_paths" >>~/.config/fish/config.fish
        echo "status is-interactive; and pyenv init --path | source" >>~/.config/fish/config.fish
        ;;
    *)
        echo "export PYENV_ROOT=\"$PYENV_ROOT\"" >>~/.bashrc
        echo "command -v pyenv >/dev/null || export PATH=\"$PYENV_ROOT/bin:$PATH\"" >>~/.bashrc
        echo "eval \"$(pyenv init -)\"" >>~/.bashrc
        if [ "$DETECTED_SHELL" = "zsh" ]; then
            echo "export PYENV_ROOT=\"$PYENV_ROOT\"" >>~/.zshrc
            echo "command -v pyenv >/dev/null || export PATH=\"$PYENV_ROOT/bin:$PATH\"" >>~/.zshrc
            echo "eval \"$(pyenv init -)\"" >>~/.zshrc
        fi
        ;;
    esac

    # Reload shell configuration
    case $DETECTED_SHELL in
    fish)
        source ~/.config/fish/config.fish
        ;;
    *)
        source ~/.bashrc
        ;;
    esac
}

# Function to install Python using pyenv
install_python() {
    if ! pyenv versions | grep -q $PYTHON_VERSION; then
        echo "Installing Python $PYTHON_VERSION using pyenv..."
        pyenv install $PYTHON_VERSION
    else
        echo "Python $PYTHON_VERSION is already installed."
    fi
    pyenv global $PYTHON_VERSION

    # Verify Python installation
    python_path=$(pyenv which python)
    echo "Python $PYTHON_VERSION installed at: $python_path"
    $python_path --version
}

# Function to set up Python virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python -m venv venv
    else
        echo "Virtual environment already exists. Updating..."
    fi

    # Activate virtual environment based on shell
    case $DETECTED_SHELL in
    fish)
        source venv/bin/activate.fish
        ;;
    *)
        source venv/bin/activate
        ;;
    esac

    echo "Upgrading pip..."
    pip install --upgrade pip

    echo "Installing required packages..."
    pip install -r requirements.txt

    if [ "$OS_TYPE" = "Darwin" ]; then
        echo "Installing macOS-specific dependencies..."
        pip install pyobjc
    fi
}

# Function to clean up previous installations
cleanup() {
    echo "Cleaning up previous installations..."
    rm -rf venv
    if command_exists pyenv; then
        pyenv uninstall -f $PYTHON_VERSION
    fi
    echo "Cleanup complete."
}

# Parse command-line arguments
CLEAN=false
PYENV_INSTALL="skip"

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
    -p | --pyenv)
        PYENV_INSTALL="$2"
        shift 2
        ;;
    --force)
        PYENV_INSTALL="force"
        shift
        ;;
    *)
        echo "Unknown option: $1"
        display_usage
        exit 1
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

# Install OS-specific dependencies
if [ "$OS_TYPE" = "Linux" ]; then
    install_ubuntu_dependencies
elif [ "$OS_TYPE" = "Darwin" ]; then
    install_macos_dependencies
else
    echo "Unsupported operating system: $OS_TYPE"
    exit 1
fi

# Install and configure pyenv
install_pyenv

# Install desired Python version
install_python

# Set up virtual environment and install dependencies
setup_venv

# Deactivate the virtual environment
case $DETECTED_SHELL in
fish)
    echo "deactivate" | source
    ;;
*)
    deactivate
    ;;
esac

echo -e "\n\n#############################################################"
echo -e "Setup complete. To activate the virtual environment, run:"
echo -e "source venv/bin/activate"
if [ "$DETECTED_SHELL" = "fish" ]; then
    echo -e "For fish shell, use: source venv/bin/activate.fish"
fi
echo -e "#############################################################\n\n"
