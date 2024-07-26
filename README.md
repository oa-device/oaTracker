# oaTracker

## Overview

oaTracker is an application for MacOS that utilizes Ultralytics and OpenCV for real-time video processing. It supports video feeds from USB cameras and provides a simple HTTP API for detection retrieval.

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

### Usage

Run the tracker:

```sh
./tracker.py --camera 0 --model yolov8n.pt --serverPort 9999 --show --fps --trackAll
```

### Command-line Options

- `--listCameras`, `-l`: List available cameras.
- `--camera`, `-c`: Select a camera as video feed using the provided ID (default is 0 - Embedded camera).
- `--model`, `-m`: Use a provided CoreML model file (default is yolov8n.pt).
- `--serverPort`, `-s`: Start HTTP server on the provided port number (default port is 9999).
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

  - Example:

  ```json
  [
    {
      "timestamp": 1623242342,
      "camera_id": 0,
      "camera_name": "FaceTime HD Camera",
      "camera_uniqueID": "3F45E80A-0176-46F7-B185-BB9E2C0E82E3",
      "model_name": "yolov8n.pt",
      "fps": 14.9,
      "boxes": [[918.01, 624.84, 1283.5, 891.73]],
      "labels": ["person"],
      "confidence": [0.9026],
      "processing_time": {
        "preprocess": 0.6,
        "inference": 24.0,
        "postprocess": 0.2
      }
    }
  ]
  ```

## Notes

- To save the installed packages to requirements.txt:

  ```sh
  # pip freeze > requirements.txt
  ```

- To deactivate the virtual environment:

  ```sh
  # deactivate
  ```

## Future Work

- Write and run unit tests.
