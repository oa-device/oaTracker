# oaCoreML

## Overview

oaCoreML is an application for MacOS that utilizes CoreML for real-time video processing. It supports video feeds from USB cameras and provides a simple HTTP API for detection retrieval.

## Checklist

- [ ] Clean the existing project files
- [ ] Initialize version control and commit the new project
- [ ] Set up dependencies
- [ ] Implement CLI options
  - [ ] `-camera id`
  - [ ] `-model pathname`
  - [ ] `-labels labels`
  - [ ] `-server port`
  - [ ] `-rtsp username:password@http://...`
- [ ] Add support for USB camera video feed
- [ ] Develop HTTP API for detection retrieval
- [ ] Write and run unit tests
- [ ] Document setup, build, and usage instructions

## Getting Started

### Prerequisites

- MacOS with ARM chip
- Python installed
- Git installed

### Setup

1. Install dependencies using pip:

   ```sh
   pip install opencv-python ultralytics
   ```

### Running the Project

1. Run the script:

   ```sh
   python tracker.py
   ```

### CLI Options

- `-camera id`: Select a camera as video feed using the provided ID.

  - Example: `sh python tracker.py -camera 1`

- `-model pathname`: Use a provided YOLO model file. The path can be relative or absolute.

  - Example: `sh python tracker.py -model /path/to/model.pt`

- `-labels labels`: Keep only the provided labels, specified as a comma-separated list.

  - Example: `sh python tracker.py -labels person,car,dog`

- `-server port`: Enable the HTTP API at the provided port number.

  - Example: `sh python tracker.py -server 8080`

- `-rtsp username:password@http://...`: Connect to a camera's RTSP stream. Supported cameras are Reolink. The application must be able to reconnect when the connection expires.
  - Example: `sh python tracker.py -rtsp username:password@http://192.168.1.100:554/`

### HTTP API

- `GET /detections`: Returns the detections of the current frame as a JSON array with boxes, labels, and confidence.

### Testing

1. Run unit tests:

   ```sh
   pytest
   ```

2. Test USB camera integration on various devices.

3. Test HTTP API with different clients.
