import cv2  # type: ignore
import platform

# Check if running on MacOS
MACOS = platform.system() == "Darwin"

if MACOS:
    from Foundation import *
    from AVFoundation import (
        AVCaptureDeviceDiscoverySession,
        AVCaptureDeviceTypeBuiltInWideAngleCamera,
        AVCaptureDeviceTypeExternal,
        AVCaptureDeviceTypeContinuityCamera,
    )

    # Lists available camera indices up to a maximum number for MacOS
    def list_available_cameras():
        devices = AVCaptureDeviceDiscoverySession.discoverySessionWithDeviceTypes_mediaType_position_(
            [AVCaptureDeviceTypeBuiltInWideAngleCamera, AVCaptureDeviceTypeExternal, AVCaptureDeviceTypeContinuityCamera], None, 0
        ).devices()

        available_cameras = []
        for index, device in enumerate(devices):
            available_cameras.append({"index": index, "id": device.uniqueID(), "name": device.localizedName()})
        return available_cameras

else:
    # Lists available camera indices up to a maximum number for other systems
    def list_available_cameras():
        available_cameras = []
        for index in range(10):  # Adjust the range as needed
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                available_cameras.append({"index": index, "id": index, "name": f"Camera {index}"})
                cap.release()
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
