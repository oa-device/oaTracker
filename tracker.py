#!/usr/bin/env python

import argparse
import threading
from src.list_cameras import list_available_cameras, list_cameras
from src.request_handler import start_server
from src.track import track


# Parses command-line arguments and initiates the appropriate functions
def main():
    global camera_info
    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from a camera.")

    # Add command-line arguments
    parser.add_argument("--listCameras", "-l", action="store_true", help="List available cameras.")
    parser.add_argument("--camera", "-c", type=int, default=0, help="Camera to use. (Default is 0 - Embedded camera)")
    parser.add_argument("--model", "-m", default="yolov8n.pt", help="ML Model to use. (Default is yolov8n.pt)")
    parser.add_argument("--serverPort", "-s", type=int, default=9999, help="Start HTTP server on port. (Default port is 9999)")
    parser.add_argument("--show", action="store_true", help="Display annotated camera stream.")
    parser.add_argument("--fps", action="store_true", help="Display fps.")
    parser.add_argument("--rtsp", help="RTSP stream instead of a camera")
    parser.add_argument("--trackAll", action="store_true", help="Track all classes instead of just 'person'")

    # Parse the arguments
    args = parser.parse_args()

    # Prepend 'models/' to the model path
    model_path = f"models/{args.model}"

    # Get camera info for tracking and listing
    cameras = list_available_cameras()
    camera_info = {str(cam["index"]): cam for cam in cameras}

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
    track(camera, model_path, args.show, args.fps, args.trackAll)


if __name__ == "__main__":
    main()
