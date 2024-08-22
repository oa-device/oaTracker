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
   source venv/bin/activate
   # For fish shell:
   # source venv/bin/activate.fish
   ```

### Configuration

Modify `config.yaml` in the root directory to change default settings:

```yaml
default_camera: 0
default_model: "yolov10n.pt"
default_server_port: 8000

cors:
  allowed_origins:
    - "http://localhost:5173"
  allowed_methods:
    - "GET"
    - "OPTIONS"
  allowed_headers:
    - "Content-Type"
```

## Usage

Run the tracker using:

```sh
./tracker.py [OPTIONS]
```

### Command-line Options

- `--listCameras`, `-l`: List available cameras.
- `--camera`, `-c`: Select a camera (default in config.yaml).
- `--model`, `-m`: Specify the model file (default in config.yaml).
- `--serverPort`, `-s`: Set HTTP server port (default in config.yaml).
- `--show`: Display annotated camera stream.
- `--fps`: Display FPS on the annotated stream.
- `--rtsp`: Use an RTSP stream or video file instead of a camera.
- `--trackAll`: Track all classes (default: only 'person').
- `--noLoop`: Do not loop video files (default: loop enabled).
- `--verbose`: Enable verbose output.

### Frequently Used Examples

1. List available cameras:

   ```sh
   ./tracker.py -l
   ```

2. Run with default camera, showing video and FPS:

   ```sh
   ./tracker.py --show --fps
   ```

3. Use a specific camera and model:

   ```sh
   ./tracker.py --camera 1 --model yolov10s.pt --show
   ```

4. Use an RTSP stream:

   ```sh
   ./tracker.py --rtsp username:password@http://192.168.1.100:554/ --show
   ```

5. Process a video file:

   ```sh
   ./tracker.py --rtsp path/to/video.mp4 --show
   ```

6. Run server on a specific port:

   ```sh
   ./tracker.py --serverPort 8080
   ```

7. Track all object classes:

   ```sh
   ./tracker.py --trackAll --show
   ```

8. Process a video file without looping:

   ```sh
   ./tracker.py --rtsp path/to/video.mp4 --show --noLoop
   ```

9. Run with verbose output:

   ```sh
   ./tracker.py --verbose
   ```

## HTTP API

The application provides a simple HTTP API for retrieving detection data. By default, the API is accessible at `http://localhost:8000` (unless a different port is specified with the `--serverPort` option).

- `GET /detections`: Returns current frame detections (boxes, labels, confidence).
- `GET /detections?from=X`: Returns unique object counts for the last X seconds (1 <= X <= 30).
- `GET /cam/collect?from=X&to=Y&cam=Z`: Returns the count of unique persons detected between X and Y milliseconds ago on camera Z.

Example requests:

```http
GET http://localhost:8000/detections?from=10
GET http://localhost:8000/cam/collect?from={from}&to={to}&cam=0
```

Example response for `/detections?from=10`:

```json
{
  "person": 2,
  "car": 1,
  "dog": 3
}
```

Note: Replace `localhost` with the appropriate IP address or hostname if accessing the API from a different machine on the network.

## Project Structure

To view the project structure:

```sh
tree -CF -L 3 -I 'venv' -I '__pycache__'
```

Install `tree`:

- MacOS: `brew install tree`
- Ubuntu: `sudo apt-get install tree`

## Development Notes

- Update `requirements.txt`:

  ```sh
  pip freeze > requirements.txt
  ```

- Deactivate virtual environment:

  ```sh
  deactivate
  ```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## Future Work

Refer to [TODO.md](TODO.md) for planned features and known issues.
