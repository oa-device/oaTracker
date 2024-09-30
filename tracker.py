#!/usr/bin/env python

import argparse
import threading
import yaml
import logging
import os
from app.utils.list_cameras import list_available_cameras, list_cameras
from app.api.request_handler import start_server
from app.vision.track import track
from app.utils.shared_state import camera_info, set_input_source
from app.utils.logger import setup_logger, get_logger, create_log_message


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


def expand_path(path):
    if path.startswith("rtsp://"):
        return path
    return os.path.abspath(os.path.expanduser(path))


def run_instance(instance_config, args):
    logger = get_logger(instance_config["name"])

    # Determine the input source
    if isinstance(instance_config["camera"], str):
        if instance_config["camera"].startswith("rtsp://") or instance_config["camera"].endswith(".mp4"):
            input_source = expand_path(instance_config["camera"])
            is_camera = False
        else:
            try:
                input_source = int(instance_config["camera"])
                is_camera = True
            except ValueError:
                logger.error(create_log_message(event="invalid_input", source=instance_config["camera"], instance=instance_config["name"]))
                return
    else:
        input_source = int(instance_config["camera"])
        is_camera = True

    # Set the input source in shared state
    set_input_source(input_source, is_camera, instance_config["name"])

    logger.info(create_log_message(event="selected_input", source=input_source, is_camera=is_camera, instance=instance_config["name"]))

    # Start the HTTP server in a separate thread
    logger.info(create_log_message(event="start_http_server", port=instance_config["api_port"], instance=instance_config["name"]))
    server_thread = threading.Thread(target=start_server, args=(instance_config,))
    server_thread.daemon = True
    server_thread.start()

    # Start tracking with the specified input source and model
    logger.info(create_log_message(event="start_tracking", input_source=input_source, model=args.model, instance=instance_config["name"]))
    track(input_source, args.model, args.show, args.fps, args.trackAll, not args.noLoop, args.verbose, instance_config["name"])


def main():
    config = load_config()

    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from multiple cameras or video sources.")

    # Add command-line arguments
    parser.add_argument("--listCameras", "-l", action="store_true", help="List available cameras.")
    parser.add_argument("--model", "-m", default=config["default_model"], help=f"ML Model to use. (Default is {config['default_model']})")
    parser.add_argument("--show", action="store_true", help="Display annotated camera stream.")
    parser.add_argument("--fps", action="store_true", help="Display fps.")
    parser.add_argument("--trackAll", action="store_true", help="Track all classes instead of just 'person'")
    parser.add_argument("--noLoop", action="store_true", help="Do not loop video files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--fileOnlyLog", action="store_true", help="Log only to file, not to console")
    parser.add_argument("--logLevel", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Set the logging level")

    # Parse the arguments
    args = parser.parse_args()

    # Setup logger
    log_level = getattr(logging, args.logLevel)
    logger = setup_logger(level=log_level, file_only=args.fileOnlyLog)
    logger.info(create_log_message(event="application_start", description="Starting tracker application"))
    logger.info(create_log_message(event="parsed_arguments", arguments=vars(args)))

    global camera_info
    # Get camera info for tracking and listing
    cameras = list_available_cameras()
    camera_info.update({str(cam["index"]): cam for cam in cameras})
    logger.info(create_log_message(event="available_cameras", cameras=camera_info))

    if args.listCameras:
        list_cameras()
        return

    instances = config["instances"]

    # Run all instances
    threads = []
    for instance_config in instances:
        thread = threading.Thread(target=run_instance, args=(instance_config, args))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
