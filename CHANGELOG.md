# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.4] - 2024-09-30

### Added

- Implemented real-time data processing in tests, replacing mock current time.
- Added support for using actual video files (video.mp4 and video2.mp4) in tests.
- Updated README.md with instructions for running tests using video files.

### Changed

- Modified test suite to use both video.mp4 and video2.mp4 for comprehensive testing.
- Updated test_api.py to incorporate real-time data and video file processing.
- Improved test coverage by testing all available API endpoints with actual video streams.

### Improved

- Enhanced overall test reliability by using real-world inputs instead of mock data.
- Increased test coverage for time-based functionalities using actual video streams.

## [0.7.3] - 2024-09-29

### Added

- Implemented comprehensive test suite for the API endpoints, particularly for `/cam/collect`.
- Added pytest and pytest-mock to the project dependencies.
- Included instructions for running tests in the README.md file.
- Created custom TestRequestHandler class for more effective testing of the RequestHandler.

### Changed

- Updated project structure in README.md to reflect the addition of the `tests/` directory.
- Improved the robustness of the `/cam/collect` endpoint testing, covering various scenarios.
- Refactored test_api.py to use pytest fixtures and parametrized tests for better organization and coverage.

### Fixed

- Resolved issues with test collection and import errors in the test suite.

## [0.7.1] - 2024-09-27

### Changed

- Improved setup script with more robust backup and restore functionality:
  - Backup is now created outside the project directory to avoid conflicts.
  - Only files and folders modified by the script are backed up.
  - Restore function now only restores modified files.
- Enhanced `configure_pyenv` function to avoid duplicate entries in shell configuration files.
- Added more safeguards throughout the script to prevent unintended system modifications.
- Improved error handling and logging throughout the setup process.

### Fixed

- Fixed issues with backup and restore logic in the setup script.
- Resolved potential conflicts with Git-tracked files during the setup process.

## [0.7.0] - 2024-09-27

### Added

- Backup functionality in setup script: Creates a restore point before making changes.
- Dry-run option (`--dry-run`) in setup script for testing without making changes.
- No-backup option (`--no-backup`) in setup script to skip creating a backup.
- Detailed logging system in setup script with creation of log files for each run.

### Changed

- Improved error handling and rollback mechanisms in setup script.
- Enhanced shell detection and configuration for bash, zsh, and fish in setup script.
- Improved safeguards for critical system directories in setup script.
- Enhanced cleanup process in setup script to be more thorough and safe.
- Improved user feedback and verbose output in setup script.

### Fixed

- Issues with setup script compatibility across different operating systems and shells.
- Potential system configuration risks during setup process.

## [0.6.0] - 2024-08-27

### Added

- New command-line option `--fileOnlyLog` to log only to file, not to console.
- New command-line option `--logLevel` to set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### Changed

- Modified logging system to allow more flexible configuration.
- Reduced default logging frequency from once per second to once per 10 seconds for performance optimization.

## [0.5.0] - 2024-08-22

### Added

- Support for RTSP streams and video files as input sources
- Flexible input source handling for both development and production scenarios
- Shared state management for input source information

### Changed

- Modified tracker.py to handle different input types (camera, RTSP, video file)
- Updated request_handler.py to use actual input source regardless of API parameter
- Refactored track.py to work consistently with various input sources
- Enhanced logging throughout the application for better debugging

### Fixed

- Resolved issues with `/cam/collect` endpoint for RTSP and video file inputs

## [0.4.0] - 2024-08-22

### Added

- Implemented structured logging system using a custom `CloudCompatibleFormatter`
- Added `create_log_message` function for creating structured log messages
- Introduced CORS handling in the HTTP API
- Added support for looping video files
- Implemented more detailed error handling and logging in the HTTP API
- Added `--verbose` flag to enable verbose output in tracking
- Introduced `PersonCounter` class for tracking unique person counts across multiple cameras

### Changed

- Renamed `src/video` directory to `src/vision`
- Updated `track` function to use the new logging system
- Improved error handling and logging throughout the application
- Enhanced `PersonCounter` class to provide more accurate counting over time periods
- Updated HTTP API to handle CORS and provide more informative responses
- Modified `config.yaml` to include CORS settings

### Fixed

- Resolved issues with video playback for file inputs
- Improved error handling in video capture initialization

## [0.3.0] - 2024-08-20

### Added

- New `/count` endpoint in the HTTP API for retrieving person counts within a specified time range and camera.
- Implemented `PersonCounter` class for tracking unique person counts.

### Changed

- Default HTTP server port changed from 9999 to 8000.
- Updated README to reflect new default port and added documentation for the new `/count` endpoint.
- Improved package structure with proper `__init__.py` files for cleaner imports.

### Fixed

- Resolved issues with import statements and module organization.

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
