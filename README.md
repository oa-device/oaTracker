# oaTracker

Real-time human detection and tracking service using YOLO models. Supports USB cameras, RTSP streams, and video files with HTTP API for macOS and Ubuntu deployment.

## Quick Start

### Prerequisites

- macOS 13+ or Ubuntu 22.04+
- Python 3.12+
- Camera device (USB or RTSP stream)
- Git and uv package manager

### Installation

```bash
# Clone repository
git clone <repository-url>
cd oaTracker

# Run setup script
./setup.sh

# Activate virtual environment
source .venv/bin/activate
```

### Configuration

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

Key configuration options:

```yaml
camera:
  uuid: "default-camera-001"
  source: "0"  # USB camera index, RTSP URL, or video file path
  loop: false  # Loop video files (true/false)

detection:
  model: "yolov8n.pt"  # Model file path
  confidence: 0.5      # Confidence threshold
  classes: [0]         # [0] = person detection only

api:
  host: "0.0.0.0"
  port: 8080
  cors_origins: ["*"]

logging:
  level: "INFO"        # DEBUG, INFO, WARNING, ERROR
  file: "logs/tracker.log"
```

### Running

```bash
# Start tracker service
./scripts/start.sh

# Or run directly
uv run python -m src.main

# With custom config
uv run python -m src.main --config config.yaml
```

## Service Management

### macOS (LaunchAgent)

```bash
# Install service
cp com.orangead.tracker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.orangead.tracker.plist

# Check status
launchctl list | grep com.orangead.tracker

# View logs
tail -f ~/orangead/tracker/logs/tracker.log

# Restart service
launchctl kickstart -k gui/$(id -u)/com.orangead.tracker

# Stop service
launchctl unload ~/Library/LaunchAgents/com.orangead.tracker.plist
```

### Ubuntu (systemd)

```bash
# Install service
sudo cp oatracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oatracker
sudo systemctl start oatracker

# Check status
sudo systemctl status oatracker

# View logs
sudo journalctl -u oatracker -f

# Restart service
sudo systemctl restart oatracker
```

## API Endpoints

### Detection Endpoints

```bash
# Get unique object count (last 30 seconds)
GET /api/detections?seconds=30
Response: {"unique_count": 5, "time_range_seconds": 30}

# Get all tracked objects
GET /api/tracked_objects
Response: [{"id": 1, "class": "person", "confidence": 0.92, ...}]

# Get detection statistics
GET /api/stats
Response: {
  "total_detections": 1234,
  "unique_objects": 45,
  "fps": 28.5,
  "uptime_seconds": 3600
}
```

### Video Stream

```bash
# MJPEG video stream
GET /video_feed
Response: multipart/x-mixed-replace (MJPEG stream)
```

### Health & Status

```bash
# Health check
GET /health
Response: {"status": "healthy", "camera": "connected", "model": "loaded"}

# Camera status
GET /api/camera/status
Response: {"connected": true, "resolution": [1280, 720], "fps": 30}
```

## Integration with oaCamBridge

oaTracker can consume video from oaCamBridge for reliable camera access:

```yaml
# config.yaml
camera:
  source: "http://localhost:8086/stream"  # oaCamBridge MJPEG stream
  # or
  source: "/tmp/webcam/img_*.jpg"  # oaCamBridge frame directory
```

Benefits:
- Decoupled camera permissions (oaCamBridge handles macOS permissions)
- Frame caching and buffering
- Independent camera and tracker restarts

## Project Structure

```
oaTracker/
├── src/                     # Source code
│   ├── main.py             # Application entry point
│   ├── detector.py         # YOLO detection engine
│   ├── tracker.py          # Object tracking logic
│   ├── api.py              # FastAPI endpoints
│   └── config.py           # Configuration management
├── models/                  # YOLO model files
│   └── yolov8n.pt          # Default model
├── logs/                    # Log files
├── config.yaml              # Runtime configuration
├── config.example.yaml      # Example configuration
├── setup.sh                 # Setup script
└── scripts/                 # Utility scripts
    └── start.sh            # Start script
```

## Common Commands

```bash
# Setup and installation
./setup.sh                   # Initial setup
./setup.sh --clean           # Clean and reinstall
./setup.sh --force           # Force pyenv reinstall

# Running
./scripts/start.sh           # Start tracker
uv run python -m src.main    # Run directly

# Testing
curl http://localhost:8080/health           # Health check
curl http://localhost:8080/api/stats        # Get statistics
curl http://localhost:8080/api/detections?seconds=10  # Get counts

# Service management (macOS)
launchctl list | grep tracker               # Check status
launchctl kickstart -k gui/$(id -u)/com.orangead.tracker  # Restart
tail -f ~/orangead/tracker/logs/tracker.log # View logs

# Service management (Ubuntu)
sudo systemctl status oatracker             # Check status
sudo systemctl restart oatracker            # Restart
sudo journalctl -u oatracker -f            # View logs
```

## Video Source Configuration

### USB Camera

```yaml
camera:
  source: "0"  # First USB camera
  # or
  source: "1"  # Second USB camera
```

### RTSP Stream

```yaml
camera:
  source: "rtsp://user:pass@192.168.1.100:8554/stream"
```

### Video File

```yaml
camera:
  source: "/path/to/video.mp4"
  loop: true  # Loop video playback
```

### oaCamBridge Integration

```yaml
camera:
  source: "http://localhost:8086/stream"  # MJPEG stream
```

## Model Configuration

### Using Pre-trained Models

```yaml
detection:
  model: "yolov8n.pt"  # Nano (fastest)
  # model: "yolov8s.pt"  # Small
  # model: "yolov8m.pt"  # Medium
  # model: "yolov8l.pt"  # Large
```

### Using Custom Models (from oaSentinel)

```yaml
detection:
  model: "models/sentinel_v1.0.onnx"  # ONNX format
  # model: "models/sentinel_v1.0.coreml"  # CoreML (macOS)
```

## Troubleshooting

### Camera Not Detected

```bash
# Check available cameras
python -c "import cv2; print([i for i in range(5) if cv2.VideoCapture(i).isOpened()])"

# macOS: Check camera permissions
# System Settings → Privacy & Security → Camera → Terminal/Python

# Try oaCamBridge integration
# Start oaCamBridge first, then configure oaTracker to use its stream
```

### Port Already in Use

```bash
# Check what's using port 8080
lsof -i :8080

# Change port in config.yaml
api:
  port: 8081  # Use different port
```

### Service Not Starting (macOS)

```bash
# Check LaunchAgent syntax
plutil -lint ~/Library/LaunchAgents/com.orangead.tracker.plist

# View system logs
log stream --predicate 'subsystem == "com.orangead.tracker"' --level debug

# Check file permissions
ls -la ~/Library/LaunchAgents/com.orangead.tracker.plist
```

### Service Not Starting (Ubuntu)

```bash
# Check service status
sudo systemctl status oatracker

# View detailed logs
sudo journalctl -u oatracker -n 50 --no-pager

# Check service file
sudo systemctl cat oatracker

# Test manual start
cd ~/orangead/tracker
source .venv/bin/activate
python -m src.main
```

### Low FPS / Performance Issues

```bash
# Use smaller model
detection:
  model: "yolov8n.pt"  # Fastest

# Reduce resolution
camera:
  width: 640
  height: 480

# Increase confidence threshold
detection:
  confidence: 0.7  # Higher = fewer but more confident detections
```

### Model Loading Errors

```bash
# Download required model
cd models/
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# Verify model file
ls -la models/yolov8n.pt

# Check model path in config
cat config.yaml | grep model
```

## Deployment

### Via oaAnsible

```bash
# Deploy to preprod environment
cd ../oaAnsible
./scripts/run projects/spectra/preprod -t tracker

# Deploy to production
./scripts/run projects/spectra/prod -t tracker

# Deploy with custom model version
./scripts/run projects/spectra/prod -t tracker \
  --extra-vars "tracker_model=sentinel_v1.2.onnx"
```

### Manual Deployment

```bash
# Transfer to device
scp -r oaTracker/ admin@device:~/orangead/tracker/

# SSH to device and setup
ssh admin@device
cd ~/orangead/tracker
./setup.sh
./scripts/start.sh
```

## Key Points

- **Port**: 8080 (configurable)
- **Service Name**: com.orangead.tracker (macOS), oatracker (Ubuntu)
- **Log Location**: ~/orangead/tracker/logs/tracker.log
- **Config File**: config.yaml (copy from config.example.yaml)
- **Model Storage**: models/ directory
- **Dependencies**: Managed by uv package manager
- **Camera Sources**: USB (0-9), RTSP URLs, video files, oaCamBridge
- **Detection Classes**: Configurable (default: person only)
- **Integration**: Works with oaCamBridge for camera access, oaSentinel for custom models
