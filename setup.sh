#!/usr/bin/env bash

set -eo pipefail

# Desired Python version
PYTHON_VERSION="3.10.11"

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${HOME}/.oatracker_setup_backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${SCRIPT_DIR}/setup_log_$(date +%Y%m%d_%H%M%S).log"
MODIFIED_FILES=()

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
  --dry-run               Perform a dry run without making any changes
  --no-backup             Skip creating a backup before making changes
  --restore <backup_dir>  Restore from a specific backup directory

Examples:
  ./setup.sh                      # Run setup with default options
  ./setup.sh --clean              # Clean up and run setup
  ./setup.sh --pyenv update       # Update existing pyenv and run setup
  ./setup.sh --force              # Force fresh pyenv installation and run setup
  ./setup.sh --clean --force      # Clean up, force fresh pyenv installation, and run setup
  ./setup.sh --dry-run            # Perform a dry run without making changes
  ./setup.sh --no-backup          # Skip creating a backup before setup
  ./setup.sh --restore /path/to/backup  # Restore from a specific backup

Note:
  - This script supports both macOS and Ubuntu.
  - It will install Homebrew on macOS if not already installed.
  - The script creates a Python virtual environment named '.venv'.
  - After running the script, activate the virtual environment with:
    source .venv/bin/activate         (for bash/zsh)
    source .venv/bin/activate.fish    (for fish shell)

EOF
}

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
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

# Function to create a backup of files that will be modified
create_backup() {
    if [ "$NO_BACKUP" = true ]; then
        log_message "Skipping backup creation as requested."
        return
    fi
    log_message "Creating backup in $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    # Backup shell configuration files
    for file in ~/.bashrc ~/.zshrc ~/.config/fish/config.fish; do
        if [ -f "$file" ]; then
            cp "$file" "$BACKUP_DIR/$(basename "$file")"
            MODIFIED_FILES+=("$file")
        fi
    done

    # Backup pyenv if it exists
    if [ -d "$HOME/.pyenv" ]; then
        cp -R "$HOME/.pyenv" "$BACKUP_DIR/pyenv_backup"
        MODIFIED_FILES+=("$HOME/.pyenv")
    fi

    # Backup virtual environment if it exists
    if [ -d "$SCRIPT_DIR/.venv" ]; then
        cp -R "$SCRIPT_DIR/.venv" "$BACKUP_DIR/venv_backup"
        MODIFIED_FILES+=("$SCRIPT_DIR/.venv")
    fi

    # Save the list of modified files
    printf "%s\n" "${MODIFIED_FILES[@]}" >"$BACKUP_DIR/modified_files.txt"

    log_message "Backup created successfully."
}

# Function to restore from backup
restore_from_backup() {
    local restore_dir="$1"
    if [ ! -d "$restore_dir" ]; then
        log_message "Error: Backup directory $restore_dir does not exist."
        exit 1
    fi

    log_message "Restoring from backup in $restore_dir"

    # Read the list of modified files
    mapfile -t MODIFIED_FILES <"$restore_dir/modified_files.txt"

    for file in "${MODIFIED_FILES[@]}"; do
        if [ -f "$restore_dir/$(basename "$file")" ]; then
            cp "$restore_dir/$(basename "$file")" "$file"
            log_message "Restored: $file"
        elif [ -d "$restore_dir/$(basename "$file")" ]; then
            rm -rf "$file"
            cp -R "$restore_dir/$(basename "$file")" "$file"
            log_message "Restored: $file"
        else
            log_message "Warning: Backup for $file not found in $restore_dir"
        fi
    done

    log_message "Restoration completed."
}

# Function to install packages on Ubuntu
install_ubuntu_dependencies() {
    log_message "Updating package lists..."
    if [ "$DRY_RUN" = false ]; then
        sudo apt-get update
        log_message "Installing build dependencies..."
        sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
            libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
            xz-utils tk-dev libffi-dev liblzma-dev python3-opencv
    else
        log_message "[DRY RUN] Would update package lists and install build dependencies."
    fi
}

# Function to install packages on macOS
install_macos_dependencies() {
    if ! command_exists brew; then
        log_message "Homebrew is not installed. Installing Homebrew..."
        if [ "$DRY_RUN" = false ]; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else
            log_message "[DRY RUN] Would install Homebrew."
        fi
    else
        log_message "Updating Homebrew..."
        if [ "$DRY_RUN" = false ]; then
            brew update
        else
            log_message "[DRY RUN] Would update Homebrew."
        fi
    fi
    log_message "Checking and installing build dependencies..."
    for pkg in openssl@3 readline sqlite xz zlib; do
        if brew list --versions $pkg >/dev/null; then
            log_message "$pkg is already installed"
        else
            log_message "Installing $pkg"
            if [ "$DRY_RUN" = false ]; then
                brew install $pkg
            else
                log_message "[DRY RUN] Would install $pkg."
            fi
        fi
    done
}

# Function to install and configure pyenv
install_pyenv() {
    PYENV_ROOT="$HOME/.pyenv"
    if [ ! -d "$PYENV_ROOT" ]; then
        log_message "pyenv is not installed. Installing pyenv..."
        if [ "$DRY_RUN" = false ]; then
            curl https://pyenv.run | bash
            configure_pyenv
        else
            log_message "[DRY RUN] Would install pyenv and configure shell."
        fi
    elif [ "$PYENV_INSTALL" = "force" ]; then
        log_message "Forcing pyenv reinstallation..."
        if [ "$DRY_RUN" = false ]; then
            rm -rf "$PYENV_ROOT"
            curl https://pyenv.run | bash
            configure_pyenv
        else
            log_message "[DRY RUN] Would force reinstall pyenv and configure shell."
        fi
    elif [ "$PYENV_INSTALL" = "update" ]; then
        log_message "Updating existing pyenv installation..."
        if [ -d "$PYENV_ROOT/.git" ]; then
            if [ "$DRY_RUN" = false ]; then
                (
                    cd "$PYENV_ROOT"
                    git pull
                )
            else
                log_message "[DRY RUN] Would update pyenv."
            fi
        else
            log_message "Existing pyenv installation is not a git repository. Skipping update."
        fi
    else
        log_message "Existing pyenv installation found. Skipping installation."
        log_message "To update or reinstall pyenv, use the -p update or -p force option."
    fi
}

# Function to configure pyenv in shell
configure_pyenv() {
    # Set up shell environment for pyenv
    case $DETECTED_SHELL in
    fish)
        config_file="$HOME/.config/fish/config.fish"
        if ! grep -q "PYENV_ROOT" "$config_file"; then
            if [ "$DRY_RUN" = false ]; then
                echo "set -Ux PYENV_ROOT $PYENV_ROOT" >>"$config_file"
                echo "set -U fish_user_paths $PYENV_ROOT/bin $fish_user_paths" >>"$config_file"
                echo "status is-interactive; and pyenv init --path | source" >>"$config_file"
            else
                log_message "[DRY RUN] Would configure pyenv for fish shell."
            fi
        else
            log_message "pyenv configuration already exists in fish config. Skipping."
        fi
        ;;
    *)
        for config_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
            if [ -f "$config_file" ] && ! grep -q "PYENV_ROOT" "$config_file"; then
                if [ "$DRY_RUN" = false ]; then
                    echo "export PYENV_ROOT=\"$PYENV_ROOT\"" >>"$config_file"
                    echo "command -v pyenv >/dev/null || export PATH=\"$PYENV_ROOT/bin:$PATH\"" >>"$config_file"
                    echo "eval \"$(pyenv init -)\"" >>"$config_file"
                else
                    log_message "[DRY RUN] Would configure pyenv for bash/zsh shell in $config_file."
                fi
            else
                log_message "pyenv configuration already exists in $config_file. Skipping."
            fi
        done
        ;;
    esac

    # Reload shell configuration
    if [ "$DRY_RUN" = false ]; then
        case $DETECTED_SHELL in
        fish)
            source "$HOME/.config/fish/config.fish"
            ;;
        *)
            source "$HOME/.bashrc"
            ;;
        esac
    else
        log_message "[DRY RUN] Would reload shell configuration."
    fi
}

# Function to install Python using pyenv
install_python() {
    if ! pyenv versions | grep -q $PYTHON_VERSION; then
        log_message "Installing Python $PYTHON_VERSION using pyenv..."
        if [ "$DRY_RUN" = false ]; then
            pyenv install $PYTHON_VERSION
        else
            log_message "[DRY RUN] Would install Python $PYTHON_VERSION using pyenv."
        fi
    else
        log_message "Python $PYTHON_VERSION is already installed."
    fi
    if [ "$DRY_RUN" = false ]; then
        pyenv global $PYTHON_VERSION
    else
        log_message "[DRY RUN] Would set Python $PYTHON_VERSION as global."
    fi

    # Verify Python installation
    if [ "$DRY_RUN" = false ]; then
        python_path=$(pyenv which python)
        log_message "Python $PYTHON_VERSION installed at: $python_path"
        $python_path --version
    else
        log_message "[DRY RUN] Would verify Python installation."
    fi
}

# Function to set up Python virtual environment
setup_venv() {
    if [ ! -d ".venv" ]; then
        log_message "Creating Python virtual environment..."
        if [ "$DRY_RUN" = false ]; then
            python -m venv .venv
        else
            log_message "[DRY RUN] Would create Python virtual environment."
        fi
    else
        log_message "Virtual environment already exists. Updating..."
    fi

    # Activate virtual environment based on shell
    if [ "$DRY_RUN" = false ]; then
        case $DETECTED_SHELL in
        fish)
            source .venv/bin/activate.fish
            ;;
        *)
            source .venv/bin/activate
            ;;
        esac
    else
        log_message "[DRY RUN] Would activate virtual environment."
    fi

    log_message "Upgrading pip..."
    if [ "$DRY_RUN" = false ]; then
        pip install --upgrade pip
    else
        log_message "[DRY RUN] Would upgrade pip."
    fi

    log_message "Installing required packages..."
    if [ "$DRY_RUN" = false ]; then
        pip install -r requirements.txt
    else
        log_message "[DRY RUN] Would install required packages from requirements.txt."
    fi

    if [ "$OS_TYPE" = "Darwin" ]; then
        log_message "Installing macOS-specific dependencies..."
        if [ "$DRY_RUN" = false ]; then
            pip install pyobjc
        else
            log_message "[DRY RUN] Would install pyobjc for macOS."
        fi
    fi
}

# Function to clean up previous installations
cleanup() {
    log_message "Cleaning up previous installations..."
    if [ "$DRY_RUN" = false ]; then
        if [ -d ".venv" ]; then
            rm -rf .venv
        fi
        if command_exists pyenv; then
            pyenv uninstall -f $PYTHON_VERSION
        fi
    else
        log_message "[DRY RUN] Would remove .venv directory and uninstall Python $PYTHON_VERSION."
    fi
    log_message "Cleanup complete."
}
# Parse command-line arguments
CLEAN=false
PYENV_INSTALL="skip"
DRY_RUN=false
NO_BACKUP=false
RESTORE_DIR=""

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
    --dry-run)
        DRY_RUN=true
        shift
        ;;
    --no-backup)
        NO_BACKUP=true
        shift
        ;;
    --restore)
        RESTORE_DIR="$2"
        shift 2
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

log_message "Detected OS: $OS_TYPE"
log_message "Detected shell: $DETECTED_SHELL"

if [ -n "$RESTORE_DIR" ]; then
    restore_from_backup "$RESTORE_DIR"
    exit 0
fi

if [ "$DRY_RUN" = true ]; then
    log_message "Performing dry run. No changes will be made."
fi

# Create backup
create_backup

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
    log_message "Unsupported operating system: $OS_TYPE"
    exit 1
fi

# Install and configure pyenv
install_pyenv

# Install desired Python version
install_python

# Set up virtual environment and install dependencies
setup_venv

# Deactivate the virtual environment
if [ "$DRY_RUN" = false ]; then
    case $DETECTED_SHELL in
    fish)
        echo "deactivate" | source
        ;;
    *)
        deactivate
        ;;
    esac
else
    log_message "[DRY RUN] Would deactivate virtual environment."
fi

log_message -e "\n\n#############################################################"
log_message "Setup complete. To activate the virtual environment, run:"
log_message "source .venv/bin/activate"
if [ "$DETECTED_SHELL" = "fish" ]; then
    log_message "For fish shell, use: source .venv/bin/activate.fish"
fi
log_message -e "#############################################################\n\n"

if [ "$DRY_RUN" = true ]; then
    log_message "Dry run completed. No changes were made. Check the log file for details: $LOG_FILE"
fi

log_message "Backup created at: $BACKUP_DIR"
log_message "To restore from this backup, run:"
log_message "./setup.sh --restore $BACKUP_DIR"
