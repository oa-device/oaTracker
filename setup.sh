#!/usr/bin/env bash

set -eo pipefail

# Define TRACKER_ROOT_DIR
TRACKER_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source utility functions
source "${TRACKER_ROOT_DIR}/scripts/setup_utils.sh"

# Global variables
TRACKER_BACKUPS_DIR="${HOME}/.oatracker_backups"
TRACKER_LOGS_DIR="${TRACKER_ROOT_DIR}/logs"
TRACKER_BACKUP_DIR="${TRACKER_BACKUPS_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
TRACKER_LOG_FILE="${TRACKER_LOGS_DIR}/setup_log_$(date +%Y%m%d_%H%M%S).log"
TRACKER_PYTHON_VERSION="3.10.11"

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

# Function to install and configure pyenv
install_pyenv() {
    local pyenv_root="$HOME/.pyenv"
    local pyenv_install=$1
    local dry_run=$2

    if [ ! -d "$pyenv_root" ]; then
        log_message "INFO" "pyenv is not installed. Installing pyenv..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            curl https://pyenv.run | bash
            configure_pyenv
        else
            log_message "INFO" "[DRY RUN] Would install pyenv and configure shell." "$TRACKER_LOG_FILE"
        fi
    elif [ "$pyenv_install" = "force" ]; then
        log_message "INFO" "Forcing pyenv reinstallation..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            rm -rf "$pyenv_root"
            curl https://pyenv.run | bash
            configure_pyenv
        else
            log_message "INFO" "[DRY RUN] Would force reinstall pyenv and configure shell." "$TRACKER_LOG_FILE"
        fi
    elif [ "$pyenv_install" = "update" ]; then
        log_message "INFO" "Updating existing pyenv installation..." "$TRACKER_LOG_FILE"
        if [ -d "$pyenv_root/.git" ]; then
            if [ "$dry_run" = false ]; then
                (
                    cd "$pyenv_root"
                    git pull
                )
            else
                log_message "INFO" "[DRY RUN] Would update pyenv." "$TRACKER_LOG_FILE"
            fi
        else
            log_message "WARNING" "Existing pyenv installation is not a git repository. Skipping update." "$TRACKER_LOG_FILE"
        fi
    else
        log_message "INFO" "Existing pyenv installation found. Skipping installation." "$TRACKER_LOG_FILE"
        log_message "INFO" "To update or reinstall pyenv, use the -p update or -p force option." "$TRACKER_LOG_FILE"
    fi
}

# Function to configure pyenv in shell
configure_pyenv() {
    local detected_shell=$(detect_shell)
    local pyenv_root="$HOME/.pyenv"

    case $detected_shell in
    fish)
        config_file="$HOME/.config/fish/config.fish"
        if ! grep -q "PYENV_ROOT" "$config_file"; then
            if [ "$DRY_RUN" = false ]; then
                echo "set -Ux PYENV_ROOT $pyenv_root" >>"$config_file"
                echo "set -U fish_user_paths $pyenv_root/bin $fish_user_paths" >>"$config_file"
                echo "status is-interactive; and pyenv init --path | source" >>"$config_file"
            else
                log_message "INFO" "[DRY RUN] Would configure pyenv for fish shell." "$TRACKER_LOG_FILE"
            fi
        else
            log_message "INFO" "pyenv configuration already exists in fish config. Skipping." "$TRACKER_LOG_FILE"
        fi
        ;;
    *)
        for config_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
            if [ -f "$config_file" ] && ! grep -q "PYENV_ROOT" "$config_file"; then
                if [ "$DRY_RUN" = false ]; then
                    echo "export PYENV_ROOT=\"$pyenv_root\"" >>"$config_file"
                    echo "command -v pyenv >/dev/null || export PATH=\"$pyenv_root/bin:$PATH\"" >>"$config_file"
                    echo "eval \"$(pyenv init -)\"" >>"$config_file"
                else
                    log_message "INFO" "[DRY RUN] Would configure pyenv for bash/zsh shell in $config_file." "$TRACKER_LOG_FILE"
                fi
            else
                log_message "INFO" "pyenv configuration already exists in $config_file. Skipping." "$TRACKER_LOG_FILE"
            fi
        done
        ;;
    esac

    # Reload shell configuration
    if [ "$DRY_RUN" = false ]; then
        case $detected_shell in
        fish)
            source "$HOME/.config/fish/config.fish"
            ;;
        *)
            source "$HOME/.bashrc"
            ;;
        esac
    else
        log_message "INFO" "[DRY RUN] Would reload shell configuration." "$TRACKER_LOG_FILE"
    fi
}

# Function to install Python using pyenv
install_python() {
    local dry_run=$1

    if ! pyenv versions | grep -q $TRACKER_PYTHON_VERSION; then
        log_message "INFO" "Installing Python $TRACKER_PYTHON_VERSION using pyenv..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            pyenv install $TRACKER_PYTHON_VERSION
        else
            log_message "INFO" "[DRY RUN] Would install Python $TRACKER_PYTHON_VERSION using pyenv." "$TRACKER_LOG_FILE"
        fi
    else
        log_message "INFO" "Python $TRACKER_PYTHON_VERSION is already installed." "$TRACKER_LOG_FILE"
    fi
    if [ "$dry_run" = false ]; then
        pyenv global $TRACKER_PYTHON_VERSION
    else
        log_message "INFO" "[DRY RUN] Would set Python $TRACKER_PYTHON_VERSION as global." "$TRACKER_LOG_FILE"
    fi

    # Verify Python installation
    if [ "$dry_run" = false ]; then
        python_path=$(pyenv which python)
        log_message "INFO" "Python $TRACKER_PYTHON_VERSION installed at: $python_path" "$TRACKER_LOG_FILE"
        $python_path --version
    else
        log_message "INFO" "[DRY RUN] Would verify Python installation." "$TRACKER_LOG_FILE"
    fi
}

# Function to set up Python virtual environment
setup_venv() {
    local dry_run=$1
    local detected_shell=$(detect_shell)

    if [ ! -d ".venv" ]; then
        log_message "INFO" "Creating Python virtual environment..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            python -m venv .venv
        else
            log_message "INFO" "[DRY RUN] Would create Python virtual environment." "$TRACKER_LOG_FILE"
        fi
    else
        log_message "INFO" "Virtual environment already exists. Updating..." "$TRACKER_LOG_FILE"
    fi

    # Activate virtual environment based on shell
    if [ "$dry_run" = false ]; then
        case $detected_shell in
        fish)
            source .venv/bin/activate.fish
            ;;
        *)
            source .venv/bin/activate
            ;;
        esac
    else
        log_message "INFO" "[DRY RUN] Would activate virtual environment." "$TRACKER_LOG_FILE"
    fi

    log_message "INFO" "Upgrading pip..." "$TRACKER_LOG_FILE"
    if [ "$dry_run" = false ]; then
        pip install --upgrade pip
    else
        log_message "INFO" "[DRY RUN] Would upgrade pip." "$TRACKER_LOG_FILE"
    fi

    log_message "INFO" "Installing required packages..." "$TRACKER_LOG_FILE"
    if [ "$dry_run" = false ]; then
        pip install -r requirements.txt
    else
        log_message "INFO" "[DRY RUN] Would install required packages from requirements.txt." "$TRACKER_LOG_FILE"
    fi

    if [ "$(uname)" = "Darwin" ]; then
        log_message "INFO" "Installing macOS-specific dependencies..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            pip install pyobjc
        else
            log_message "INFO" "[DRY RUN] Would install pyobjc for macOS." "$TRACKER_LOG_FILE"
        fi
    fi
}

# Main setup function
main() {
    local clean=false
    local pyenv_install="skip"
    local dry_run=false
    local no_backup=false
    local restore_dir=""

    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        -h | --help)
            display_usage
            exit 0
            ;;
        -c | --clean)
            clean=true
            shift
            ;;
        -p | --pyenv)
            pyenv_install="$2"
            shift 2
            ;;
        --force)
            pyenv_install="force"
            shift
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        --no-backup)
            no_backup=true
            shift
            ;;
        --restore)
            restore_dir="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            display_usage
            exit 1
            ;;
        esac
    done

    # Create necessary directories
    mkdir -p "$TRACKER_BACKUPS_DIR" "$TRACKER_LOGS_DIR"

    log_message "INFO" "Detected OS: $(uname)" "$TRACKER_LOG_FILE"
    log_message "INFO" "Detected shell: $(detect_shell)" "$TRACKER_LOG_FILE"

    if [ -n "$restore_dir" ]; then
        restore_from_backup "$restore_dir" "$TRACKER_LOG_FILE"
        exit 0
    fi

    if [ "$dry_run" = true ]; then
        log_message "INFO" "Performing dry run. No changes will be made." "$TRACKER_LOG_FILE"
    fi

    # Create backup
    create_backup "$TRACKER_BACKUP_DIR" "$TRACKER_LOG_FILE" "$no_backup"

    # Clean up old backups and logs
    cleanup_old_files "$TRACKER_BACKUPS_DIR" "$TRACKER_LOGS_DIR" "$TRACKER_LOG_FILE"

    # Perform cleanup if requested
    if $clean; then
        log_message "INFO" "Cleaning up previous installations..." "$TRACKER_LOG_FILE"
        if [ "$dry_run" = false ]; then
            rm -rf .venv
        else
            log_message "INFO" "[DRY RUN] Would remove .venv directory." "$TRACKER_LOG_FILE"
        fi
    fi

    # Install OS-specific dependencies
    if [ "$(uname)" = "Linux" ]; then
        install_ubuntu_dependencies "$TRACKER_LOG_FILE" "$dry_run"
    elif [ "$(uname)" = "Darwin" ]; then
        install_macos_dependencies "$TRACKER_LOG_FILE" "$dry_run"
    else
        log_message "ERROR" "Unsupported operating system: $(uname)" "$TRACKER_LOG_FILE"
        exit 1
    fi

    # Install and configure pyenv
    install_pyenv "$pyenv_install" "$dry_run"

    # Install desired Python version
    install_python "$dry_run"

    # Set up virtual environment and install dependencies
    setup_venv "$dry_run"

    # Deactivate the virtual environment
    if [ "$dry_run" = false ]; then
        case $(detect_shell) in
        fish)
            echo "deactivate" | source
            ;;
        *)
            deactivate
            ;;
        esac
    else
        log_message "INFO" "[DRY RUN] Would deactivate virtual environment." "$TRACKER_LOG_FILE"
    fi

    log_message "INFO" "Setup complete." "$TRACKER_LOG_FILE"
    log_message "INFO" "To activate the virtual environment, run:" "$TRACKER_LOG_FILE"
    log_message "INFO" "source .venv/bin/activate" "$TRACKER_LOG_FILE"
    if [ "$(detect_shell)" = "fish" ]; then
        log_message "INFO" "For fish shell, use: source .venv/bin/activate.fish" "$TRACKER_LOG_FILE"
    fi

    if [ "$dry_run" = true ]; then
        log_message "INFO" "Dry run completed. No changes were made. Check the log file for details: $TRACKER_LOG_FILE" "$TRACKER_LOG_FILE"
    fi

    log_message "INFO" "Backup created at: $TRACKER_BACKUP_DIR" "$TRACKER_LOG_FILE"
    log_message "INFO" "To restore from this backup, run:" "$TRACKER_LOG_FILE"
    log_message "INFO" "./setup.sh --restore $TRACKER_BACKUP_DIR" "$TRACKER_LOG_FILE"
}

# Run the main function
main "$@"
