#!/usr/bin/env python

import cv2  # type: ignore
from ultralytics import YOLO  # type: ignore
import argparse
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import json
from datetime import datetime
from Foundation import *
from AVFoundation import (
    AVCaptureDeviceDiscoverySession,
    AVCaptureDeviceTypeBuiltInWideAngleCamera,
    AVCaptureDeviceTypeExternal,
    AVCaptureDeviceTypeContinuityCamera,
)
import os

# Set environment variable to suppress OpenCV logging
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Global variables to store detection results and camera information
latest_detections = []
camera_info = {}


# Lists available camera indices up to a maximum number
def list_available_cameras():
    devices = AVCaptureDeviceDiscoverySession.discoverySessionWithDeviceTypes_mediaType_position_(
        [AVCaptureDeviceTypeBuiltInWideAngleCamera, AVCaptureDeviceTypeExternal, AVCaptureDeviceTypeContinuityCamera], None, 0
    ).devices()

    available_cameras = []
    for index, device in enumerate(devices):
        available_cameras.append({"index": index, "id": device.uniqueID(), "name": device.localizedName()})
    return available_cameras


# Prints the list of available cameras with more informative names
def list_cameras():
    available_cameras = list_available_cameras()
    max_name_length = max(len(camera["name"]) for camera in available_cameras)
    for camera in available_cameras:
        index = camera["index"]
        name = camera["name"]
        unique_id = camera["id"]
        print(f"Camera {index}: {name:<{max_name_length}} (ID: {unique_id})")


# Handles HTTP requests and returns the latest detection results for GET requests to /detections
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/detections":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            global latest_detections
            # Pretty-print JSON response
            pretty_json = json.dumps(latest_detections, indent=4)
            self.wfile.write(pretty_json.encode())
        else:
            self.send_response(302)
            self.send_header("Location", "/detections")
            self.end_headers()


# Starts the HTTP server on the specified port number
def start_server(port_number):
    server_address = ("", port_number)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Starting server on port {port_number}")
    httpd.serve_forever()


# Captures video from the specified camera, runs YOLO object detection, and optionally displays the annotated frames
def track(camera_id, model_name, show_flag, fps_flag, track_all):
    global latest_detections, camera_info
    model = YOLO(model_name)

    # Initialize video capture object
    vid = cv2.VideoCapture(camera_id)
    prev_time = 0

    # Fetch camera name and unique ID from camera info
    camera_details = camera_info.get(str(camera_id), {})
    camera_name = camera_details.get("name", "Unknown Camera")
    camera_uniqueID = camera_details.get("id", "Unknown ID")

    while True:
        # Capture video frame-by-frame
        success, frame = vid.read()
        if success:
            # Run YOLO object detection, filtering for "person" class (index 0) if not track_all
            classes = [0] if not track_all else None
            results = model.track(frame, persist=False, classes=classes)

            # Get the current timestamp in epoch format
            timestamp = int(datetime.now().timestamp())

            # Calculate FPS
            current_time = time.time()
            fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
            prev_time = current_time

            # Update latest detections
            latest_detections = [
                {
                    "timestamp": timestamp,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "camera_uniqueID": camera_uniqueID,
                    "model_name": model_name,
                    "fps": fps,
                    "boxes": result.boxes.xywh.cpu().tolist(),
                    "labels": ["person" if i == 0 else result.names[i] for i in result.boxes.cls.cpu().tolist()],
                    "confidence": result.boxes.conf.cpu().tolist(),
                    "processing_time": {
                        "preprocess": results[0].speed["preprocess"] if results else None,
                        "inference": results[0].speed["inference"] if results else None,
                        "postprocess": results[0].speed["postprocess"] if results else None,
                    },
                }
                for result in results
                if len(result.boxes) > 0
            ]

            if show_flag:
                # Annotate frame with detection results
                annotated_frame = results[0].plot()

                if fps_flag:
                    # Display FPS on the frame
                    annotated_frame = cv2.putText(
                        annotated_frame,
                        f"FPS: {fps:.2f}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )
                # Display the annotated frame
                cv2.imshow("YOLOv8 Tracking", annotated_frame)

                # Quit the loop when 'q' key is pressed
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    # Release the video capture object and close display windows
    vid.release()
    cv2.destroyAllWindows()


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
    track(camera, args.model, args.show, args.fps, args.trackAll)


if __name__ == "__main__":
    main()
