import cv2  # type: ignore
import os
import time
import platform
import sys
from ultralytics import YOLO  # type: ignore
from datetime import datetime
from src.shared_state import latest_detections, camera_info, add_detection
from collections import Counter

# Set environment variable to suppress OpenCV logging
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Check if running on MacOS
MACOS = platform.system() == "Darwin"


def sticky_print(message):
    # Move cursor to the beginning of the line and clear the line
    sys.stdout.write("\033[H\033[J")
    # Print the message
    sys.stdout.write(message)
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

    # Get frame resolution
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print("\n\033[1;32m--- Tracking Started ---\033[0m")  # Bold Green color
    print(f"Camera: {camera_name}")
    print(f"Model: {model_name}")
    print(f"Resolution: {width}x{height}")
    print("Press 'q' to stop tracking\n")

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
            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                detection = {
                    "timestamp": timestamp,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "camera_uniqueID": camera_uniqueID,
                    "model_name": model_name,
                    "fps": fps,
                    "tracked_objects": [
                        {
                            "id": int(id) if id is not None else None,
                            "label": model.names[int(cls)],
                            "box": box,  # Remove .tolist() as box is already a list
                            "confidence": float(conf),  # Convert to float for JSON serialization
                        }
                        for id, cls, box, conf in zip(
                            boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes),
                            boxes.cls.int().cpu().tolist(),
                            boxes.xywh.cpu().tolist(),
                            boxes.conf.cpu().tolist(),
                        )
                    ],
                    "processing_time": {
                        "preprocess": results[0].speed["preprocess"],
                        "inference": results[0].speed["inference"],
                        "postprocess": results[0].speed["postprocess"],
                    },
                }
                latest_detections.append(detection)
                add_detection(detection)

            # Prepare sticky print information
            elapsed_time = time.time() - start_time
            avg_fps = frame_count / elapsed_time

            # Count detected objects
            detected_objects = Counter()
            for result in results:
                for cls in result.boxes.cls.cpu().tolist():
                    detected_objects[result.names[int(cls)]] += 1

            total_objects = sum(detected_objects.values())

            # Prepare the info string
            info = "\033[1;36m--- Tracking Info ---\033[0m\n"
            info += f"Camera: {camera_name} | Resolution: {width}x{height}\n"
            info += f"FPS: {fps:.2f} | Avg FPS: {avg_fps:.2f} | Elapsed Time: {elapsed_time:.2f}s\n"
            info += f"Total Detected Objects: {total_objects}\n"
            for obj, count in detected_objects.items():
                info += f"  - {obj}: {count}\n"
            if results:
                info += f"Processing Times: "
                info += f"Preprocess: {results[0].speed['preprocess']:.2f}ms | "
                info += f"Inference: {results[0].speed['inference']:.2f}ms | "
                info += f"Postprocess: {results[0].speed['postprocess']:.2f}ms\n"

            sticky_print(info)

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

    print("\n\033[1;31m--- Tracking Stopped ---\033[0m")  # Red color
