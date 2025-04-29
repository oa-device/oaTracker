# oaTracker

## Overview

oaTracker is an internal application for MacOS and Ubuntu that utilizes Ultralytics and OpenCV for real-time video processing. It supports video feeds from USB cameras, RTSP streams, and video files, providing a simple HTTP API for detection retrieval.

## Features

- **Real-time Object Detection**: Uses YOLO models for efficient object detection.
- **Object Tracking**: Tracks individual objects across video frames.
- **Unique Object Counting**: Counts unique objects detected within a specified time range.
- **Time-based Queries**: Query detections within the last X seconds (1 <= X <= 30).
- **Multiple Video Sources**: Supports USB cameras, RTSP streams, and video files.
- **HTTP API**: Simple API for retrieving detection data with CORS support.
- **Configurable Settings**: Easy configuration via `config.yaml` file.
- **Structured Logging**: Comprehensive logging system for debugging and monitoring.
- **Video Looping**: Option to loop video file inputs for continuous processing.
- **Flexible Logging Options**: Control log output and log level via command-line arguments.

## Getting Started

### Prerequisites

- MacOS or Ubuntu
- Xcode (for MacOS)
- Git

### Setup

1. Clone the repository:

   ```sh
   git clone <repository-url>
   cd oaTracker
   ```

2. Run the setup script:

   ```sh
   ./setup.sh
   ```

   The setup script has several options:

   - `--clean` or `-c`: Clean up previous installations before setup
   - `--pyenv <option>` or `-p <option>`: Specify pyenv installation option:
     - `skip`: Skip pyenv installation/update (default)
     - `update`: Update existing pyenv installation
     - `force`: Force a fresh pyenv installation
   - `--force`: Equivalent to `--pyenv force`

   Examples:

   ```sh
   ./setup.sh --clean                # Clean up and run setup
   ./setup.sh --pyenv update         # Update existing pyenv and run setup
   ./setup.sh --force                # Force fresh pyenv installation and run setup
   ./setup.sh --clean --force        # Clean up, force fresh pyenv installation, and run setup
   ```

3. Activate the virtual environment:

   ```sh
   source .venv/bin/activate
   # For fish shell:
   # source .venv/bin/activate.fish
   ```

### Configuration

Clone `config.example.yaml` to `config.yaml` in the root directory to change cam uuid:
## Usage

Run the tracker using:

```sh
./scripts/start.sh
```
