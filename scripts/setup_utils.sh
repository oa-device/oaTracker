#!/usr/bin/env bash

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to log messages with colors in terminal and without colors in log file
log_message() {
    local level=$1
    local message=$2
    local log_file=$3
    local color=""

    case $level in
    "INFO")
        color=$GREEN
        ;;
    "WARNING")
        color=$YELLOW
        ;;
    "ERROR")
        color=$RED
        ;;
    esac

    # Log to file without color
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >>"$log_file"

    # Print to terminal with color
    if [ -t 1 ]; then
        echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message${NC}"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
    fi
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the current shell
detect_shell() {
    local current_shell=$(basename "$SHELL")
    local running_shell=$(basename "$0")

    if [ "$running_shell" = "bash" ] || [ "$running_shell" = "zsh" ] || [ "$running_shell" = "fish" ]; then
        echo "$running_shell"
    elif [ "$current_shell" = "bash" ] || [ "$current_shell" = "zsh" ] || [ "$current_shell" = "fish" ]; then
        echo "$current_shell"
    else
        echo "unknown"
    fi
}

# Function to set up pyenv in shell configuration
setup_pyenv_in_shell() {
    local detected_shell=$(detect_shell)
    local config_file=""

    case $detected_shell in
    bash)
        config_file="$HOME/.bashrc"
        ;;
    zsh)
        config_file="$HOME/.zshrc"
        ;;
    fish)
        config_file="$HOME/.config/fish/config.fish"
        ;;
    *)
        log_message "ERROR" "Unsupported shell: $detected_shell" "$TRACKER_LOG_FILE"
        return 1
        ;;
    esac

    # Add pyenv configuration to shell config file
    if [ ! -f "$config_file" ]; then
        log_message "INFO" "Creating $config_file" "$TRACKER_LOG_FILE"
        touch "$config_file"
    fi

    if [ "$detected_shell" = "fish" ]; then
        # Use fish to check and add the configuration
        fish -c "
            if not contains $TRACKER_PYENV_ROOT/bin \$PATH
                set -Ua fish_user_paths $TRACKER_PYENV_ROOT/bin
            end
            if not grep -q 'pyenv init' $config_file
                echo '$TRACKER_PYENV_BIN init - | source' >> $config_file
            end
        "
        log_message "INFO" "pyenv has been set up in your fish configuration" "$TRACKER_LOG_FILE"
        log_message "INFO" "Please restart your Fish shell or run 'source $config_file' to apply changes" "$TRACKER_LOG_FILE"
    else
        if ! grep -q "pyenv init" "$config_file"; then
            log_message "INFO" "Adding pyenv configuration to $config_file" "$TRACKER_LOG_FILE"
            cat <<EOF >>"$config_file"

# pyenv configuration
export PATH="$TRACKER_PYENV_ROOT/bin:\$PATH"
eval "\$($TRACKER_PYENV_BIN init --path)"
eval "\$($TRACKER_PYENV_BIN init -)"

EOF
            log_message "INFO" "pyenv has been set up in your $detected_shell configuration" "$TRACKER_LOG_FILE"
        else
            log_message "INFO" "pyenv configuration already exists in $config_file" "$TRACKER_LOG_FILE"
        fi
    fi
}

# Function to create a backup of files that will be modified
create_backup() {
    local backup_dir=$1
    local log_file=$2
    local no_backup=$3

    if [ "$no_backup" = true ]; then
        log_message "INFO" "Skipping backup creation as requested." "$log_file"
        return
    fi

    log_message "INFO" "Creating backup in $backup_dir" "$log_file"
    mkdir -p "$backup_dir"

    # Backup shell configuration files
    for file in ~/.bashrc ~/.zshrc ~/.config/fish/config.fish; do
        if [ -f "$file" ]; then
            cp "$file" "$backup_dir/$(basename "$file")"
        fi
    done

    # Backup pyenv if it exists
    if [ -d "$TRACKER_PYENV_ROOT" ]; then
        cp -R "$TRACKER_PYENV_ROOT" "$backup_dir/pyenv_backup"
    fi

    # Backup virtual environment if it exists
    if [ -d "$TRACKER_ROOT_DIR/.venv" ]; then
        cp -R "$TRACKER_ROOT_DIR/.venv" "$backup_dir/venv_backup"
    fi

    log_message "INFO" "Backup created successfully." "$log_file"
}

# Function to restore from backup
restore_from_backup() {
    local restore_dir=$1
    local log_file=$2

    if [ ! -d "$restore_dir" ]; then
        log_message "ERROR" "Backup directory $restore_dir does not exist." "$log_file"
        exit 1
    fi

    log_message "INFO" "Restoring from backup in $restore_dir" "$log_file"

    # Restore shell configuration files
    for file in ~/.bashrc ~/.zshrc ~/.config/fish/config.fish; do
        if [ -f "$restore_dir/$(basename "$file")" ]; then
            cp "$restore_dir/$(basename "$file")" "$file"
            log_message "INFO" "Restored: $file" "$log_file"
        fi
    done

    # Restore pyenv if backup exists
    if [ -d "$restore_dir/pyenv_backup" ]; then
        rm -rf "$TRACKER_PYENV_ROOT"
        cp -R "$restore_dir/pyenv_backup" "$TRACKER_PYENV_ROOT"
        log_message "INFO" "Restored: $TRACKER_PYENV_ROOT" "$log_file"
    fi

    # Restore virtual environment if backup exists
    if [ -d "$restore_dir/venv_backup" ]; then
        rm -rf "$TRACKER_ROOT_DIR/.venv"
        cp -R "$restore_dir/venv_backup" "$TRACKER_ROOT_DIR/.venv"
        log_message "INFO" "Restored: $TRACKER_ROOT_DIR/.venv" "$log_file"
    fi

    log_message "INFO" "Restoration completed." "$log_file"
}

# Function to clean up old backups and logs
cleanup_old_files() {
    local backups_dir=$1
    local logs_dir=$2
    local log_file=$3

    log_message "INFO" "Cleaning up old backups and logs..." "$log_file"

    # Keep only the 5 most recent backups
    if [ -d "$backups_dir" ]; then
        cd "$backups_dir"
        ls -t | tail -n +6 | xargs -I {} rm -rf {}
        cd - >/dev/null
    fi

    # Keep only the 10 most recent log files
    if [ -d "$logs_dir" ]; then
        cd "$logs_dir"
        ls -t | tail -n +11 | xargs -I {} rm -f {}
        cd - >/dev/null
    fi

    log_message "INFO" "Cleanup of old backups and logs completed." "$log_file"
}

# Function to install packages on Ubuntu
install_ubuntu_dependencies() {
    local log_file=$1
    local dry_run=$2

    log_message "INFO" "Updating package lists..." "$log_file"
    if [ "$dry_run" = false ]; then
        sudo apt-get update
        log_message "INFO" "Installing build dependencies..." "$log_file"
        sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
            libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
            xz-utils tk-dev libffi-dev liblzma-dev python3-opencv
    else
        log_message "INFO" "[DRY RUN] Would update package lists and install build dependencies." "$log_file"
    fi
}

# Function to install packages on macOS
install_macos_dependencies() {
    local log_file=$1
    local dry_run=$2

    if ! command_exists "$TRACKER_BREW_PATH"; then
        log_message "INFO" "Homebrew is not installed. Installing Homebrew..." "$log_file"
        if [ "$dry_run" = false ]; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else
            log_message "INFO" "[DRY RUN] Would install Homebrew." "$log_file"
        fi
    else
        log_message "INFO" "Updating Homebrew..." "$log_file"
        if [ "$dry_run" = false ]; then
            "$TRACKER_BREW_PATH" update
        else
            log_message "INFO" "[DRY RUN] Would update Homebrew." "$log_file"
        fi
    fi

    log_message "INFO" "Checking and installing build dependencies..." "$log_file"
    for pkg in openssl@3 readline sqlite xz zlib; do
        if "$TRACKER_BREW_PATH" list --versions "$pkg" >/dev/null; then
            log_message "INFO" "$pkg is already installed" "$log_file"
        else
            log_message "INFO" "Installing $pkg" "$log_file"
            if [ "$dry_run" = false ]; then
                "$TRACKER_BREW_PATH" install "$pkg"
            else
                log_message "INFO" "[DRY RUN] Would install $pkg." "$log_file"
            fi
        fi
    done
}

# Export functions
export -f log_message
export -f command_exists
export -f detect_shell
export -f setup_pyenv_in_shell
export -f create_backup
export -f restore_from_backup
export -f cleanup_old_files
export -f install_ubuntu_dependencies
export -f install_macos_dependencies
