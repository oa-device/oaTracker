# oaCoreML

## Overview

oaCoreML is an application for MacOS that utilizes CoreML for real-time video processing. It supports video feeds from USB cameras and provides a simple HTTP API for detection retrieval.

## Checklist

- [x] Create and switch to the `dev_kai` branch
- [x] Clean the existing project files
- [x] Create a new Xcode project named `oaCoreML`
- [ ] Initialize version control and commit the new project
- [ ] Set up dependencies using Swift Package Manager
- [ ] Implement CLI options
  - [ ] `-listCameras`
  - [ ] `-listScreens`
  - [ ] `-camera id`
  - [ ] `-video pathname`
  - [ ] `-model pathname`
  - [ ] `-fullScreen id`
  - [ ] `-overlay`
  - [ ] `-labels labels`
  - [ ] `-loop`
  - [ ] `-server port`
  - [ ] `-rtsp username:password@http://...`
- [ ] Add support for USB camera video feed
- [ ] Develop HTTP API for detection retrieval
- [ ] Write and run unit tests
- [ ] Document setup, build, and usage instructions

## Getting Started

### Prerequisites

- MacOS with ARM chip
- Xcode installed
- Git installed

### Setup

1. Install dependencies using Swift Package Manager:

   ```sh
   swift package init
   swift package update
   ```

### Building the Project

1. Clean the current build:

   ```sh
   xcodebuild clean
   ```

2. Rebuild the project:

   ```sh
   xcodebuild build -project oaCoreML.xcodeproj
   ```

### CLI Options

- `-listCameras`: List available cameras and exit.

  - Example: `sh oaCoreML -listCameras`

- `-listScreens`: List available screens and exit.

  - Example: `sh oaCoreML -listScreens`

- `-camera id`: Select a camera as video feed using the provided ID.

  - Example: `sh oaCoreML -camera 1`

- `-video pathname`: Use a video file as the source. The path can be relative or absolute.

  - Example: `sh oaCoreML -video /path/to/video.mp4`

- `-model pathname`: Use a provided CoreML model file. The path can be relative or absolute.

  - Example: `sh oaCoreML -model /path/to/model.mlmodel`
  - Note: If no model is provided, the internal model `yolov3.mlmodel` is used.

- `-fullScreen id`: Select the screen as video output using the provided ID. The video is full screen without any UI component.

  - Example: `sh oaCoreML -fullScreen 2`

- `-overlay`: Overlay detection boxes, labels, fps, and the number of items detected on the video.

  - Example: `sh oaCoreML -overlay`

- `-labels labels`: Keep only the provided labels, specified as a comma-separated list.

  - Example: `sh oaCoreML -labels person,car,dog`

- `-loop`: Loop the video if the mode is `-video`. Has no effect in `-camera` mode.

  - Example: `sh oaCoreML -loop`

- `-server port`: Enable the HTTP API at the provided port number.

  - Example: `sh oaCoreML -server 8080`

- `-rtsp username:password@http://...`: Connect to a camera's RTSP stream. Supported cameras are Reolink. The application must be able to reconnect when the connection expires.
  - Example: `sh oaCoreML -rtsp username:password@http://192.168.1.100:554/`

### HTTP API

- `GET /detections`: Returns the detections of the current frame as a JSON array with boxes, labels, and confidence.

### Testing

1. Run unit tests:

   ```sh
   xcodebuild test -project oaCoreML.xcodeproj
   ```

2. Test USB camera integration on various devices.

3. Test HTTP API with different clients.
