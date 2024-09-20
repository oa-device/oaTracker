from json import dump, dumps
import multiprocessing
import os
import time
import platform
import sys
import torch # type: ignore
import cv2 # type: ignore
from ultralytics import YOLO, settings # type: ignore
from collections import Counter

from app.config import get_config
from app.utils.shared_state import Detection, latest_detections, add_detection
from app.utils.person_counter import PersonCounter
from app.utils.logger import get_logger, create_log_message

from typing import  Any, List, TypedDict

logger = get_logger(__name__)


# required for multiprocessing using gpu, see https://pytorch.org/docs/stable/notes/multiprocessing.html#cuda-in-multiprocessing
# must stay at the top
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

# Disabled Google Analytics tracking from Yolov8
if settings.get("sync") == True:
    settings["sync"] = False
    settings.save()

# dimension of the camera output
IMG_WIDTH = 640
IMG_HEIGHT = 400

# torch device detection, enables cross-platform hardware acceleration
TORCH_DEVICE = (
    "cuda"
    if hasattr(torch, "cuda") and torch.cuda.is_available()
    else "mps"
    if hasattr(torch, "has_mps") and torch.has_mps
    else "cpu"
)
torch.tensor([0]).to(device=TORCH_DEVICE)

YOLO_DEVICE = (
    0
    if TORCH_DEVICE == "cuda"
    else "mps"
    if  TORCH_DEVICE == "mps"
    else "cpu"
)

config = get_config()

# Set environment variable to suppress OpenCV logging
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# Check if running on MacOS
MACOS = platform.system() == "Darwin"

def sticky_print(message) -> None:
    sys.stdout.write("\033[H\033[J")
    sys.stdout.write(message)
    sys.stdout.flush()


def initialize_video_capture(camera_id: int) -> cv2.VideoCapture:
    vid = cv2.VideoCapture(camera_id)
    if not vid.isOpened():
        logger.error(create_log_message(event="video_capture_error", error="Failed to open video source", camera_id=camera_id))
        raise ValueError(f"Failed to open video source: {camera_id}")
    return vid


def load_model(model_name) -> YOLO:
    if model_name.startswith("models/"):
        model_path = model_name
    elif os.path.isfile(model_name):
        model_path = model_name
    else:
        model_path = f"models/{model_name}"
    logger.info(create_log_message(event="load_model", model_path=model_path))
    return YOLO(model_path)


def process_frame(model, frame, classes):
    return model.track(frame, persist=True, classes=classes, verbose=False, device=YOLO_DEVICE, tracker="bytetrack.yaml")


def update_detections(results, model, input_source, fps) -> Any | None:
    timestamp = int(time.time() * 1000)
    latest_detections.clear()
    if results and len(results[0].boxes) > 0:
        boxes = results[0].boxes
        print(results[0].speed)
        detection = Detection({
            "timestamp": timestamp,
            "input_source": input_source,
            "fps": fps,
            "tracked_objects": [ # type: ignore
                {
                    "id": int(id) if id is not None else None,
                    "label": model.names[int(cls)],
                    "box": box,
                    "confidence": float(conf),
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
        })
        
        latest_detections.append(detection)
        add_detection(detection)

        logger.debug(create_log_message(event="update_detections", input_source=input_source, objects_count=len(detection["tracked_objects"])))

        return detection
    return None


def display_frame(frame, results, fps, fps_flag) -> Any:
    annotated_frame = results[0].plot()
    if fps_flag:
        cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow("YOLOv8 Tracking", annotated_frame)
    return cv2.waitKey(1) & 0xFF == ord("q")


def format_tracking_info(input_source, width, height, fps, avg_fps, elapsed_time, total_objects, detected_objects, results) -> str:
    info = "\033[1;36m--- Tracking Info ---\033[0m\n"
    info += f"Input Source: {input_source} | Resolution: {width}x{height}\n"
    info += f"FPS: {fps:.2f} | Avg FPS: {avg_fps:.2f} | Elapsed Time: {elapsed_time:.2f}s\n"
    info += f"Total Detected Objects: {total_objects}\n"
    for obj, count in detected_objects.items():
        info += f"  - {obj}: {count}\n"
    if results:
        info += f"Processing Times: "
        info += f"Preprocess: {results[0].speed['preprocess']:.2f}ms | "
        info += f"Inference: {results[0].speed['inference']:.2f}ms | "
        info += f"Postprocess: {results[0].speed['postprocess']:.2f}ms\n"
    return info


def log_tracking_info(frame_count, fps, avg_fps, elapsed_time, detected_objects, results, input_source) -> None:
    log_message = create_log_message(
        event="tracking_info",
        frame=frame_count,
        fps=round(fps, 2),
        avg_fps=round(avg_fps, 2),
        elapsed_time=round(elapsed_time, 2),
        detected_objects=dict(detected_objects),
        processing_times={k: round(v, 2) for k, v in results[0].speed.items()} if results else {},
        input_source=input_source,
    )
    logger.info(log_message)


def track(input_source, model_name=None, show_flag=True, fps_flag=True, track_all=False, loop_video=True, verbose=False) -> None:
    logger.info(
        create_log_message(
            event="tracking_start",
            input_source=input_source,
            model_name=model_name,
            show_flag=show_flag,
            fps_flag=fps_flag,
            track_all=track_all,
            loop_video=loop_video,
            verbose=verbose,
        )
    )

    model_name = model_name or config["default_model"]
    frame_count: float = 0
    start_time = time.time()
    prev_time: float = 0
        
    try:
        model = load_model(model_name)
        vid = initialize_video_capture(input_source)
        vid.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_WIDTH)
        vid.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_HEIGHT)
        width = IMG_WIDTH
        height = IMG_HEIGHT

        logger.info(create_log_message(event="tracking_setup", input_source=input_source, model=model_name, resolution=f"{width}x{height}"))

        person_counter = PersonCounter.get_counter(str(input_source))
        last_log_time = start_time
        log_interval = 10  # Log every 10 seconds

        detected_objects: Counter[Any] = Counter()

        while True:
            success, frame = vid.read()
            if not success:
                if loop_video and isinstance(input_source, str) and os.path.isfile(input_source):
                    vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = vid.read()
                if not success:
                    logger.info(create_log_message(event="video_end", reason="End of video stream", input_source=input_source))
                    break

            frame_count += 1
            classes = [0] if not track_all else None
            results = process_frame(model, frame, classes)

            current_time = time.time()
            fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
            prev_time = current_time

            detection = update_detections(results, model, input_source, fps)
            if detection:
                person_counter.update(detection["tracked_objects"])

                detected_objects.clear()
                detected_objects.update(obj["label"] for obj in detection["tracked_objects"])
                total_objects = sum(detected_objects.values())
                elapsed_time = current_time - start_time
                avg_fps = frame_count / elapsed_time if elapsed_time > 0 else 0

                if current_time - last_log_time >= log_interval:
                    log_tracking_info(frame_count, fps, avg_fps, elapsed_time, detected_objects, results, input_source)
                    last_log_time = current_time

                if verbose:
                    info = format_tracking_info(input_source, width, height, fps, avg_fps, elapsed_time, total_objects, detected_objects, results)
                    sticky_print(info)

            if show_flag and display_frame(frame, results, fps, True):
                logger.info(create_log_message(event="tracking_interrupted", reason="User interrupted", input_source=input_source))
                break

    except Exception as e:
        logger.exception(e)
        logger.error(create_log_message(event="tracking_error", error=str(e), input_source=input_source))
    finally:
        if "vid" in locals():
            vid.release()
        if "show_flag" in locals() and show_flag:
            cv2.destroyAllWindows()

        logger.info(
            create_log_message(event="tracking_stop", total_frames=frame_count, total_time=time.time() - start_time, input_source=input_source)
        )


# Test the logger in this file
logger.info(create_log_message(event="module_load", module="track.py"))
