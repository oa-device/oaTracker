import cv2  # type: ignore
from ultralytics import YOLO  # type: ignore
import os
import time
from datetime import datetime

# Set environment variable to suppress OpenCV logging
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Global variables to store detection results and camera information
latest_detections = []
camera_info = {}
try:
    from Foundation import *
    from AVFoundation import (
        AVCaptureDeviceDiscoverySession,
        AVCaptureDeviceTypeBuiltInWideAngleCamera,
        AVCaptureDeviceTypeExternal,
        AVCaptureDeviceTypeContinuityCamera,
    )

    MACOS = True
except ImportError:
    MACOS = False


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
            results = model.track(frame, persist=True, classes=classes)

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

            if show_flag and MACOS:
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
    if MACOS:
        cv2.destroyAllWindows()
