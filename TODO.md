# TODO List for oaTracker

## Code Structure

- [x] Reorganize the project into a more modular structure
- [x] Implement a configuration file (config.yaml) for easier management of default settings
- [ ] Use tools like pip-compile or poetry for better dependency management
- [x] Implement structured logging system

## Documentation

- [x] Enhance README with detailed setup and usage instructions
- [ ] Create comprehensive API documentation using Swagger or ReDoc
- [ ] Add inline comments to explain complex parts of the code
- [ ] Create a CONTRIBUTING.md file with guidelines for contributors
- [x] Keep CHANGELOG.md up-to-date with recent changes

## Features

- [x] Implement object tracking across video frames
- [x] Add unique object counting within specified time ranges
- [x] Create HTTP API for retrieving detection data
- [x] Add support for RTSP streams and video files as input sources
- [x] Implement more advanced filtering options for the API
- [ ] Add support for multiple camera streams simultaneously
- [ ] Explore and implement additional YOLO models for improved detection accuracy
- [ ] Add option to save processed video with annotations
- [ ] Implement alert system for specific detection scenarios
- [x] Add CORS support to the HTTP API
- [x] Implement video looping for file inputs

## Setup and Installation

- [x] Create comprehensive setup script with usage guide
- [x] Improve cross-platform compatibility (MacOS and Ubuntu)
- [ ] Add option to specify Python version in setup script
- [ ] Implement automatic dependency updates in setup script
- [ ] Add system requirement checks in setup script (e.g., available disk space, RAM)

## Testing

- [ ] Implement unit tests for critical components
- [ ] Add integration tests for the HTTP API
- [ ] Set up continuous integration (CI) using GitHub Actions or GitLab CI

## Error Handling and Logging

- [x] Implement more robust error handling throughout the application
- [x] Add a logging system to help with debugging and monitoring
- [ ] Implement log rotation and archiving

## Performance Optimization

- [ ] Profile the application to identify bottlenecks
- [ ] Implement caching mechanisms where appropriate
- [x] Optimize person counting algorithm for better performance over time periods

## Containerization

- [ ] Create a Dockerfile to containerize the application

## Code Quality

- [ ] Implement linting (e.g., flake8, pylint)
- [ ] Implement formatting (e.g., black)
- [ ] Set up pre-commit hooks to ensure code quality before commits

## Scalability

- [ ] Consider implementing a message queue system for handling multiple video streams or high loads

## Security

- [ ] Implement authentication and authorization for the API
- [ ] Set up a process for regularly updating dependencies to patch security vulnerabilities

## Monitoring and Analytics

- [ ] Implement monitoring tools (e.g., Prometheus, Grafana) for tracking application performance and usage

## User Interface

- [ ] Create a web-based dashboard for easier interaction with the tracker

Remember to update this TODO list as you complete tasks or identify new areas for improvement. This list will help guide the project's development and make it easier for contributors to understand the project's direction and outstanding tasks.
