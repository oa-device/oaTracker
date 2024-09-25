#!/usr/bin/env python

import argparse
from dataclasses import dataclass
import json
import logging
from typing import Any, Literal
from app.config import  get_config
from app.utils.list_cameras import list_available_cameras, list_cameras
from app.utils.logger import create_log_message, setup_logger

@dataclass
class Args:
    listCameras: bool
    camera: int
    model: str
    classes: str
    fileOnlyLog: bool
    rtsp: str
    logLevel: Literal["DEBUG"] | Literal["INFO"] | Literal["WARNING"] | Literal["ERROR"] | Literal["CRITICAL"]
    input_source: str | int
    is_camera: bool
    camera_info: dict[str, Any]

def parse_args() -> Args:
    config = get_config()

    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from a camera or video source.")

    # Add command-line arguments
    parser.add_argument("--listCameras", "-l", action="store_true", help="List available cameras.")
    parser.add_argument(
        "--camera", "-c", type=int, default=config["default_camera"], help=f"Camera to use. (Default is {config['default_camera']} - Embedded camera)"
    )
    parser.add_argument("--model", "-m", type=str, default=config["default_model"], help=f"ML Model to use. (Default is {config['default_model']})")
    parser.add_argument(
        "--serverPort",
        "-s",
        type=int,
        default=config["default_server_port"],
        help=f"Start HTTP server on port. (Default port is {config['default_server_port']})",
    )
    parser.add_argument("--rtsp",type=str,  help="RTSP stream or video file instead of a camera")
    parser.add_argument("--classes",type=str,  help="Comma separated list of classes, default 0 (person)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--fileOnlyLog", action="store_true", help="Log only to file, not to console")
    parser.add_argument("--logLevel", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Set the logging level")

    # Parse the arguments
    args: ArgsNamespace = parser.parse_args() # type: ignore

    # Setup logger
    log_level = getattr(logging, args.logLevel)
    logger = setup_logger(level=log_level, file_only=args.fileOnlyLog)
    logger.info(create_log_message(event="application_start", description="Starting tracker application"))

    logger.info(create_log_message(event="parsed_arguments", arguments=vars(args)))

    # Get camera info for tracking and listing
    cameras = list_available_cameras()
    args.camera_info = dict()
    args.camera_info.update({str(cam["index"]): cam for cam in cameras})
    logger.info(create_log_message(event="available_cameras", cameras=args.camera_info))

    if args.listCameras:
        list_cameras()
        quit()
        return

    # Determine the input source
    if args.rtsp:
        args.input_source = args.rtsp
        args.is_camera = False
    else:
        args.input_source = args.camera
        args.is_camera = True

    logger.info(create_log_message(event="selected_input", source=args.input_source, is_camera=args.is_camera))

    # Start tracking with the specified input source and model
    logger.info(create_log_message(event="start_tracking", input_source=args.input_source, model=args.model))
    
    return args
