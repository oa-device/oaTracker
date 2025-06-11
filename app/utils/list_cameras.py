import os
import cv2  # type: ignore

def list_available_cameras():
    level = os.environ.get("OPENCV_LOG_LEVEL")
    os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
    available_cameras = []
    for index in range(10):  # Adjust the range as needed
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            available_cameras.append(
                {"index": index, "id": index, "name": f"Camera {index}"}
            )
            cap.release()
    if not level:
        del os.environ["OPENCV_LOG_LEVEL"]
    else:
        os.environ["OPENCV_LOG_LEVEL"] = level
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
