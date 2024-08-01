#!/usr/bin/env python

import argparse
import threading
import yaml

from src.utils.list_cameras import list_available_cameras, list_cameras
from src.api.request_handler import start_server
from src.video.track import track
from src.utils.shared_state import camera_info


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


def main():
    global camera_info
    config = load_config()

    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from a camera.")

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
    parser.add_argument("--rtsp", help="RTSP stream instead of a camera")
    parser.add_argument("--trackAll", action="store_true", help="Track all classes instead of just 'person'")

    # Parse the arguments
    args = parser.parse_args()

    # Get camera info for tracking and listing
    cameras = list_available_cameras()
    camera_info.update({str(cam["index"]): cam for cam in cameras})

    if args.listCameras:
        list_cameras()
        return

    # Start the HTTP server in a separate thread
    server_thread = threading.Thread(target=start_server, args=(args.serverPort,))
    server_thread.daemon = True
    server_thread.start()

    camera = args.camera
    if args.rtsp:
        camera = args.rtsp

    # Start tracking with the specified camera or RTSP stream and model
    track(camera, args.model, args.show, args.fps, args.trackAll)


if __name__ == "__main__":
    main()
