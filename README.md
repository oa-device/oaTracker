# oaTracker

## Overview

oaTracker is an application for MacOS that utilizes Ultralytics and OpenCV for real-time video processing. It supports video feeds from USB cameras and provides a simple HTTP API for detection retrieval.

## New Features

- **Object Tracking**: The application now uses YOLO's built-in tracking feature to track individual objects across frames.
- **Unique Object Counting**: The HTTP API now provides counts of unique objects detected within a specified time range.
- **Time-based Queries**: You can now query for detections within the last X seconds (1 <= X <= 30).
- **Modular Structure**: The project has been reorganized into a more modular structure for better maintainability.
- **Configuration File**: A `config.yaml` file has been added for easier management of default settings.

## Project Structure

To view the current project structure, run the following command from the project root:

```sh
tree -CF -L 3 -I 'oa-env' -I '__pycache__'
```

This command will display a tree-like structure of the project, excluding the virtual environment (`oa-env`) and Python cache files (`__pycache__`).

If you don't have the `tree` command installed, you can install it using:

- On macOS with Homebrew: `brew install tree`
- On Ubuntu or Debian: `sudo apt-get install tree`

Note: The actual structure may vary slightly depending on your current development state.

## Getting Started

### Prerequisites

- MacOS or Ubuntu
- Xcode installed
- Git installed
- Python 3 installed

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

3. To activate the virtual environment:

   ```sh
   source oa-env/bin/activate
   # For fish shell:
   # source oa-env/bin/activate.fish
   ```

### Configuration

The `config.yaml` file in the root directory contains default settings for the application. You can modify these settings to change the default behavior:

```yaml
default_camera: 0
default_model: "yolov10n.pt"
default_server_port: 9999
```

### Usage

Run the tracker:

```sh
./tracker.py --camera 0 --model yolov10n.pt --serverPort 9999 --show --fps --trackAll
```

### Command-line Options

- `--listCameras`, `-l`: List available cameras.
- `--camera`, `-c`: Select a camera as video feed using the provided ID (default is set in config.yaml).
- `--model`, `-m`: Use a provided CoreML model file (default is set in config.yaml).
- `--serverPort`, `-s`: Start HTTP server on the provided port number (default port is set in config.yaml).
- `--show`: Display annotated camera stream.
- `--fps`: Display fps on the annotated stream.
- `--rtsp`: Use an RTSP stream instead of a camera.
- `--trackAll`: Track all classes instead of just 'person'.

### Frequently Used Examples

- List available cameras:

  ```sh
  ./tracker.py -l
  ```

- Show the camera stream with annotations and FPS:

  ```sh
  ./tracker.py --show --fps
  ```

- Use an RTSP stream:

  ```sh
  ./tracker.py --rtsp username:password@http://192.168.1.100:554/
  ```

- Use a video file as the source:

  ```sh
  ./tracker.py --rtsp path/to/video.mp4
  ```

- Start the server on port 8080:

  ```sh
  ./tracker.py --serverPort 8080
  ```

### HTTP API

- `GET /detections`: Returns the detections of the current frame as a JSON array with boxes, labels, and confidence.

- `GET /detections?from=X`: Returns the count of unique objects detected in the last X seconds (1 <= X <= 30).

  Example response:

  ```json
  {
    "person": 2,
    "car": 1,
    "dog": 3
  }
  ```

## Development

### Changelog

We use [Semantic Versioning](https://semver.org/) for version numbers. All notable changes are documented in the [CHANGELOG.md](CHANGELOG.md) file.

### Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Notes

- To save the installed packages to requirements.txt:

  ```sh
  pip freeze > requirements.txt
  ```

- To deactivate the virtual environment:

  ```sh
  deactivate
  ```

## Future Work

For a list of planned features and known issues, see the [TODO.md](TODO.md) file.
