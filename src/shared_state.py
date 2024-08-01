from collections import deque
import time

MAX_HISTORY_SECONDS = 30

latest_detections = []
camera_info = {}

detection_history = deque(maxlen=MAX_HISTORY_SECONDS * 30)  # Assuming 30 FPS max


def add_detection(detection):
    detection_history.append((time.time(), detection))


def get_detections_from(seconds_ago):
    current_time = time.time()
    return [d for t, d in detection_history if current_time - t <= seconds_ago]


def get_unique_object_counts(seconds_ago):
    detections = get_detections_from(seconds_ago)
    unique_objects = {}
    for detection in detections:
        for obj in detection["tracked_objects"]:
            if obj["id"] is not None:
                # If we have a tracking ID, use it
                obj_id = (obj["label"], obj["id"])
                if obj_id not in unique_objects or unique_objects[obj_id]["timestamp"] < detection["timestamp"]:
                    unique_objects[obj_id] = {"timestamp": detection["timestamp"], "label": obj["label"]}
            else:
                # If no tracking ID, count each detection as unique
                unique_objects[len(unique_objects)] = {"timestamp": detection["timestamp"], "label": obj["label"]}

    return {
        label: sum(1 for obj in unique_objects.values() if obj["label"] == label) for label in set(obj["label"] for obj in unique_objects.values())
    }
