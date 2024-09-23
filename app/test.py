import time
import cv2
from ultralytics import YOLO

model = YOLO("yolov10n.pt")

cap = cv2.VideoCapture(0)

# Loop through the video frames
while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()

    if success:
        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        before = time.monotonic()
        results = model.track(frame, persist=True, verbose=False, classes=0, device=0,
                        imgsz=640,
                        conf=0.02,
                        iou=0.6,)
        print(f"{(time.monotonic() - before) * 1000} ms")
    else:
        # Break the loop if the end of the video is reached
        break
