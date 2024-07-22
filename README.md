<p align="center">
<img width="128" src="CoreMLPlayer/Assets.xcassets/AppIcon.appiconset/Icon-128@2x.png">
</p>

<h1 align="center">CoreML Player</h1>
<p align="center">Try your CoreML Models on multiple videos and images easily and quickly.</p>

---

# Requirements

macOS 13.0+

Currently supports Object Detection and Classification models that can be used with Vision framework.

# Features

- Control main configuration via CLI
- Support for USB camera video feed
- Simple HTTP API to retrieve current detections

## CLI Options

### -listCameras

List available cameras and exit. Each camera has a Unique ID allowing selecting it with the option `-camera`.

### -listScreens

List available screens and exit. Each screen has a Unique ID allowing selecting it with the option `-fullscreen`.

### -camera id

Use the provided ID to select a camera as the video feed. The camera ID is provided with the option `-listCameras`. This option cannot be used with the option `-video` as they are mutually exclusive.

### -video pathname

Use the provided video file as the source. The path can be relative or absolute.

### -model pathname

Use the provided model file. The path can be relative or absolute. The provided model is a CoreML model. If no model is provided, the internal model `yolov3.mlmodel` is used.

### -fullScreen id

Use the provided ID to select the screen as video output. The video is full screen without any UI component. Note that the video and/or the screen can be portrait or landscape. The video will be displayed with a maximum fitting size while keeping its aspect ratio.

### -overlay

Overlay detection boxes, labels, FPS, and the current number of items detected on the video.

### -labels labels

Keep only the provided labels. They are provided as a comma-separated list. Overlays will then only display these labels.

### -loop

If the mode is `-video`, loop the video. Has no effect in `-camera` mode.

### -server port

Enable the following HTTP API at the provided port number:

#### GET /detections

Returns the detections of the current frame (JSON array: boxes, labels, confidence).

# Screenshots

![videos](https://user-images.githubusercontent.com/80475242/216794698-49bfb420-9850-4895-9ca9-ad722f7745d1.png)
<sub>[Video by Brett Sayles from Pexels](https://www.pexels.com/video/dog-waiting-along-the-sidewalk-2048206/)</sub>

![images](https://user-images.githubusercontent.com/80475242/216794699-2c5c733a-aeb5-4b99-a2c8-e0e743074213.png)
<sub>[Photo by Patrick Tomasso from Unsplash](https://unsplash.com/photos/nApljhT9kfM)</sub>

---

For demo purposes and being able to test the functionality quickly, the project includes a sample mlmodel file:

- YOLOv3Tiny: [https://github.com/pjreddie/darknet](https://github.com/pjreddie/darknet) (downloaded from [Apple's website](https://developer.apple.com/machine-learning/models/))
