# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-08-02

### Added

- Improved setup script with comprehensive usage guide
- New command-line options for setup script (`--clean`, `--pyenv`, `--force`)
- Non-destructive pyenv installation option in setup script
- Support for RTSP streams and video files as input sources
- CHANGELOG.md to track project changes

### Changed

- Enhanced README with emphasis on setup and usage examples
- Reorganized project structure for better modularity
- Moved API-related code to src/api/
- Moved utility functions to src/utils/
- Moved video processing code to src/video/

### Fixed

- Issues with pyenv installation and updates in setup script
- Improved cross-platform compatibility (MacOS and Ubuntu)
- Enhanced project maintainability and readability

## [0.1.0] - 2024-08-01

### Added

- Initial release of oaTracker
- Real-time object detection using YOLO models
- Object tracking across video frames
- Unique object counting within specified time ranges
- Time-based queries for detections
- HTTP API for retrieving detection data
- Support for USB cameras
- Modular project structure
- Configuration file (config.yaml) for default settings

### Fixed

- Initial bug fixes and performance improvements
