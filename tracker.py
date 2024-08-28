#!/usr/bin/env python

import argparse
import threading
import yaml
import logging
from src.utils.list_cameras import list_available_cameras, list_cameras
from src.api.request_handler import start_server
from src.vision.track import track
from src.utils.shared_state import camera_info, set_input_source
from src.utils.logger import setup_logger, get_logger, create_log_message


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


def main():
    config = load_config()

    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from a camera or video source.")

    # Add command-line arguments
    parser.add_argument("--listCameras", "-l", action="store_true", help="List available cameras.")
    parser.add_argument(
        "--camera", "-c", type=int, default=config["default_camera"], help=f"Camera to use. (Default is {config['default_camera']} - Embedded camera)"
    )
    parser.add_argument("--model", "-m", default=config["default_model"], help=f"ML Model to use. (Default is {config['default_model']})")
    parser.add_argument(
        "--serverPort",
        "-s",
        type=int,
        default=config["default_server_port"],
        help=f"Start HTTP server on port. (Default port is {config['default_server_port']})",
    )
    parser.add_argument("--show", action="store_true", help="Display annotated camera stream.")
    parser.add_argument("--fps", action="store_true", help="Display fps.")
    parser.add_argument("--rtsp", help="RTSP stream or video file instead of a camera")
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

    # Start the HTTP server in a separate thread
    logger.info(create_log_message(event="start_http_server", port=args.serverPort))
    server_thread = threading.Thread(target=start_server, args=(args.serverPort,))
    server_thread.daemon = True
    server_thread.start()

    # Determine the input source
    if args.rtsp:
        input_source = args.rtsp
        is_camera = False
    else:
        input_source = args.camera
        is_camera = True

    # Set the input source in shared state
    set_input_source(input_source, is_camera)

    logger.info(create_log_message(event="selected_input", source=input_source, is_camera=is_camera))

    # Start tracking with the specified input source and model
    logger.info(create_log_message(event="start_tracking", input_source=input_source, model=args.model))
    track(input_source, args.model, args.show, args.fps, args.trackAll, not args.noLoop, args.verbose)


if __name__ == "__main__":
    main()
