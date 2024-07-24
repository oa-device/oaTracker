#!/usr/bin/env python

# import the opencv library
import cv2  # type: ignore
from ultralytics import YOLO  # type: ignore
import argparse
import time


def list_available_cameras(max_cameras=10):
    available_cameras = []
    for camera_index in range(max_cameras):
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            available_cameras.append(camera_index)
            cap.release()
    return available_cameras


def list_cameras():
    # TODO: make this dynamic
    print("0: USB WebCam")
    print("1: Embedded camera")
    print("2: iPhone")


def start_server(port_number):
    print(port_number)


def track(camera_id, model_name, show_flag, fps_flag):
    model = YOLO(model_name)

    # define a video capture object
    vid = cv2.VideoCapture(camera_id)

    prev_time = 0

    while True:
        # Capture the video frame
        # by frame
        success, frame = vid.read()

        if success:

            results = model.track(frame, persist=False, show=show_flag, classes=[0])

            if show_flag:
                boxes = results[0].boxes.xywh.cpu()

                # Visualize the results on the frame
                annotated_frame = results[0].plot()

                if fps_flag:
                    current_time = time.time()
                    fps = 1 / (current_time - prev_time)
                    prev_time = current_time
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

                # the 'q' button is set as the
                # quitting button you may use any
                # desired button of your choice
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    # After the loop release the cap object
    vid.release()
    # Destroy all the windows
    cv2.destroyAllWindows()


def main():
    # Create the parser
    parser = argparse.ArgumentParser(prog="tracker", description="Detect and track object from a camera.")

    # Add arguments
    parser.add_argument("--listCameras", "-l", action="store_true", help="List available cameras.")
    parser.add_argument("--camera", "-c", type=int, default=0, help="Camera to use. (Defalt is 0 - Embedded camera)")
    parser.add_argument("--model", "-m", default="yolov8n.pt", help="ML Model to use. (Default is yolov8n.pt)")
    parser.add_argument(
        "--serverPort", "-s", type=int, default=9999, help="Start HTTP server on port. (Defalt port is 9999)"
    )
    parser.add_argument("--show", action="store_true", help="Display annotated camera stream.")
    parser.add_argument("--fps", action="store_true", help="Display fps.")

    # Parse the arguments
    args = parser.parse_args()

    if args.listCameras:
        list_cameras()
        return

    start_server(args.serverPort)

    track(args.camera, args.model, args.show, args.fps)


if __name__ == "__main__":
    main()
