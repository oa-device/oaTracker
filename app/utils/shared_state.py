from collections import deque
import time

MAX_HISTORY_SECONDS = 30

latest_detections = {}
camera_info = {}

detection_history = {}

input_sources = {}
is_camera = {}


def add_detection(detection, instance_name):
    if instance_name not in detection_history:
        detection_history[instance_name] = deque(maxlen=MAX_HISTORY_SECONDS * 30)  # Assuming 30 FPS max
    detection_history[instance_name].append((time.time(), detection))


def get_detections_from(seconds_ago, instance_name):
    if instance_name not in detection_history:
        return []
    current_time = time.time()
    return [d for t, d in detection_history[instance_name] if current_time - t <= seconds_ago]


def get_unique_object_counts(seconds_ago, instance_name):
    detections = get_detections_from(seconds_ago, instance_name)
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


def set_input_source(source, camera=True, instance_name=None):
    if instance_name is None:
        raise ValueError("instance_name must be provided")
    input_sources[instance_name] = source
    is_camera[instance_name] = camera


def get_input_source(instance_name=None):
    if instance_name is None:
        raise ValueError("instance_name must be provided")
    return input_sources.get(instance_name), is_camera.get(instance_name)
