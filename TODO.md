# TODO List for oaTracker

## Code Structure

- [x] Reorganize the project into a more modular structure
- [x] Implement a configuration file (config.yaml) for easier management of default settings
- [x] Implement structured logging system
- [ ] Use tools like pip-compile or poetry for better dependency management

## Documentation

- [x] Enhance README with detailed setup and usage instructions
- [x] Keep CHANGELOG.md up-to-date with recent changes
- [x] Add visualization of setup process in README.md
- [ ] Create comprehensive API documentation using Swagger or ReDoc
- [ ] Add inline comments to explain complex parts of the code
- [ ] Create a CONTRIBUTING.md file with guidelines for contributors

## Features

- [x] Implement object tracking across video frames
- [x] Add unique object counting within specified time ranges
- [x] Create HTTP API for retrieving detection data
- [x] Add support for RTSP streams and video files as input sources
- [x] Implement more advanced filtering options for the API
- [x] Add CORS support to the HTTP API
- [x] Implement video looping for file inputs
- [x] Implement flexible logging options (file-only logging, log level selection)
- [x] Enhance health endpoint with detailed system status information
- [ ] Add support for multiple camera streams simultaneously
- [ ] Explore and implement additional YOLO models for improved detection accuracy
- [ ] Add option to save processed video with annotations
- [ ] Implement alert system for specific detection scenarios
- [ ] Implement periodic health checks and automatic recovery for degraded states

## Setup and Installation

- [x] Create comprehensive setup script with usage guide
- [x] Improve cross-platform compatibility (MacOS and Ubuntu)
- [x] Implement robust backup and restore functionality in setup script
- [x] Add dry-run option to setup script
- [x] Enhance shell compatibility (bash, zsh, fish) in setup script
- [ ] Add option to specify Python version in setup script
- [ ] Implement automatic dependency updates in setup script
- [ ] Add system requirement checks in setup script (e.g., available disk space, RAM)
- [ ] Implement a rollback feature for failed installations

## Testing

- [x] Implement unit tests for critical components
- [x] Add integration tests for the HTTP API
- [x] Implement comprehensive tests for the `/cam/collect` endpoint
- [ ] Add tests for other API endpoints (e.g., `/detections`, `/health`)
- [ ] Set up continuous integration (CI) using GitHub Actions or GitLab CI
- [ ] Add tests for setup script to ensure cross-platform compatibility
- [ ] Implement test coverage reporting

## Error Handling and Logging

- [x] Implement more robust error handling throughout the application
- [x] Add a logging system to help with debugging and monitoring
- [x] Implement log rotation and archiving
- [ ] Add log analysis tools or scripts for easier troubleshooting
- [ ] Implement more detailed error reporting in setup script

## Performance Optimization

- [x] Optimize logging frequency for better performance
- [ ] Profile the application to identify bottlenecks
- [ ] Implement caching mechanisms where appropriate
- [x] Optimize person counting algorithm for better performance over time periods

## Containerization

- [ ] Create a Dockerfile to containerize the application
- [ ] Ensure setup script works correctly within a containerized environment

## Code Quality

- [ ] Implement linting (e.g., flake8, pylint)
- [ ] Implement formatting (e.g., black)
- [ ] Set up pre-commit hooks to ensure code quality before commits

## Scalability

- [ ] Consider implementing a message queue system for handling multiple video streams or high loads

## Security

- [ ] Implement authentication and authorization for the API
- [ ] Set up a process for regularly updating dependencies to patch security vulnerabilities
- [ ] Implement secure handling of sensitive information in setup script (e.g., API keys, passwords)

## Monitoring and Analytics

- [x] Implement basic system monitoring through enhanced health endpoint
- [ ] Implement monitoring tools (e.g., Prometheus, Grafana) for tracking application performance and usage
- [ ] Add telemetry to setup script to track usage and identify common issues

## User Interface

- [ ] Create a web-based dashboard for easier interaction with the tracker
- [ ] Develop a graphical interface for the setup process

Remember to update this TODO list as you complete tasks or identify new areas for improvement. This list will help guide the project's development and make it easier for contributors to understand the project's direction and outstanding tasks.
