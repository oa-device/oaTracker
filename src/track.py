import cv2  # type: ignore
import os
import time
import platform
import sys
from ultralytics import YOLO  # type: ignore
from datetime import datetime
from src.shared_state import latest_detections, camera_info

# Set environment variable to suppress OpenCV logging
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Check if running on MacOS
MACOS = platform.system() == "Darwin"

def sticky_print(message):
    sys.stdout.write('\r' + message)
    sys.stdout.flush()

# Captures video from the specified camera, runs YOLO object detection, and optionally displays the annotated frames
def track(camera_id, model_name, show_flag, fps_flag, track_all):
    global latest_detections
    model = YOLO(model_name)

    # Initialize video capture object
    vid = cv2.VideoCapture(camera_id)
    prev_time = 0

    # Fetch camera name and unique ID from camera info
    camera_details = camera_info.get(str(camera_id), {})
    camera_name = camera_details.get("name", "Unknown Camera")
    camera_uniqueID = camera_details.get("id", "Unknown ID")

    frame_count = 0
    start_time = time.time()

    while True:
        # Capture video frame-by-frame
        success, frame = vid.read()
        if success:
            # Run YOLO object detection, filtering for "person" class (index 0) if not track_all
            frame_count += 1
            classes = [0] if not track_all else None
            results = model.track(frame, persist=True, classes=classes, verbose=False, device="mps", tracker="bytetrack.yaml")

            # Get the current timestamp in epoch format
            timestamp = int(datetime.now().timestamp())

            # Calculate FPS
            current_time = time.time()
            fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
            prev_time = current_time

            # Update latest detections
            latest_detections.clear()
            latest_detections.extend(
                [
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
            )

            # Prepare sticky print information
            elapsed_time = time.time() - start_time
            avg_fps = frame_count / elapsed_time
            detected_objects = sum(len(result.boxes) for result in results)

            info = f"Camera: {camera_name} | FPS: {fps:.2f} | Avg FPS: {avg_fps:.2f} | Detected Objects: {detected_objects} | Elapsed Time: {elapsed_time:.2f}s"
            sticky_print(info)

            if show_flag and MACOS:
                annotated_frame = results[0].plot()
                if fps_flag:
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
                cv2.imshow("YOLOv8 Tracking", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    vid.release()
    if MACOS:
        cv2.destroyAllWindows()
    
    print("\nTracking stopped.")  # Add a newline after stopping