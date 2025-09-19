import mmap
import os
from queue import Queue
import threading
import time
import traceback
from typing import Any, NamedTuple
import boto3
import torch
import ultralytics.engine.results
from app.counters import Counters
from app.parse_args import Args
from app.processes.counter.bot_sort import BOTSORT
from app.processes.counter.video_capture_threading import VideoCaptureThreading
from app.utils.logger import get_logger
from cv2 import imencode
import cv2
import numpy as np


from ultralytics.utils import YAML, IterableSimpleNamespace
from multiprocessing.synchronize import Event as EventClass
from ultralytics import YOLO

from app.utils.mmap import mmap_context, mmap_write, pathname_img
from app.utils.stop_detection import major_error
from app.utils.tracker_persistence import load_tracker, save_tracker

logger = get_logger(__name__)


LOOP_TIMEOUT = 10.0  # 10 seconds timeout before restarting


class Tracked(NamedTuple):
    xyxy: tuple[float, float, float, float]
    id: int
    conf: float
    label: str


def byte_size(s):
    return len(s.encode("utf-8"))


def log_visualization(
    client, frame, plot, shared_memory_img: mmap.mmap, log_to_cloud: bool, camId: str
) -> None:
    try:
        _, img = imencode(".webp", plot, [int(cv2.IMWRITE_WEBP_QUALITY), 10])
        if _:
            mmap_write(shared_memory_img, 512000, img.tobytes())

        if log_to_cloud:
            client.put_object(
                Body=img.tobytes(),
                Bucket="detectiondb-prod",
                Key=f"cams/img/detection_{camId}.webp",
                ACL="public-read",
                ContentType="image/webp",
            )
            _, cam = imencode(".webp", frame, [int(cv2.IMWRITE_WEBP_QUALITY), 10])
            if _:
                client.put_object(
                    Body=cam.tobytes(),
                    Bucket="detectiondb-prod",
                    Key=f"cams/img/cam_{camId}.webp",
                    ACL="public-read",
                    ContentType="image/webp",
                )
    except:
        print("logging viz error")


def second_thread(q, boot_int, camId, access_key, secret_key):
    try:
        last_update = 0.0
        client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        with mmap_context(pathname_img, 512000) as shared_memory_img:
            while True:
                try:
                    (frame, plot) = q.get(timeout=LOOP_TIMEOUT)
                    while True:
                        try:
                            log_to_cloud = time.monotonic() - last_update > 2

                            try:
                                log_visualization(
                                    client,
                                    frame,
                                    plot,
                                    shared_memory_img,
                                    log_to_cloud,
                                    camId,
                                )
                            except:
                                time.sleep(0.05)
                                pass

                            if log_to_cloud:
                                client.put_object(
                                    Body=f"""boot,cam_id,last_update\n{int(boot_int / 10)},{camId},{int(time.time())}""".encode(
                                        "utf-8"
                                    ),
                                    Bucket="detectiondb-prod",
                                    Key=f"cams/stats/{camId}.csv",
                                    ACL="public-read",
                                    ContentType="text/csv",
                                )
                                last_update = time.monotonic()
                                print("Sending images and debug data to cloud !")
                            break
                        except Exception:
                            time.sleep(0.05)
                            pass
                except Exception as e:
                    tbe = traceback.TracebackException.from_exception(e)
                    stack_frames = traceback.extract_stack()
                    tbe.stack.extend(stack_frames)
                    formatted_traceback = "".join(tbe.format())
                    print(f"Formatted Traceback:\n{formatted_traceback}")
                    print("raw err", e)
                    major_error(camId, "Error in detection second thread", e)
                    return
    except Exception as e:
        tbe = traceback.TracebackException.from_exception(e)
        stack_frames = traceback.extract_stack()
        tbe.stack.extend(stack_frames)
        formatted_traceback = "".join(tbe.format())
        print(f"Formatted Traceback:\n{formatted_traceback}")
        print("raw err", e)
        major_error(camId, "Error in detection second thread", e)


class CounterLoop:
    def __init__(self, args: Args, all_counters, server_stopped: EventClass):
        try:
            self.running = True
            self.args = args

            self.fps = 0.0

            self.inference_perf_data: list[float] = []
            self.inference_perf_mean = 0.0

            self.tick = 0

            self.model = YOLO(
                f"{os.path.dirname(__file__)}/../../../models/{self.args.model}",
                "track",
            )

            self.counters = Counters(args, all_counters)
            self.classes = self.counters.classes
            self.names = {
                0: "person", 2: "car", 3: "motorcycle", 5: "bus"
            }
            self.results = None

            self.last_console_log = time.time() + 5
            self.errors = 0
            self.freeze_frame_counter = 0

            self.tracker_cfg = IterableSimpleNamespace(
                **YAML.load(f"{os.path.dirname(__file__)}/botsort_custom.yaml")
            )
            self.result = None
            tracker = BOTSORT(self.tracker_cfg, 30)
            self.tracker = load_tracker(tracker)

            self.log: dict[str, Any] = {}
            self.server_stopped = server_stopped
            self.cam_thread = VideoCaptureThreading(self.args.camId)
            self.cam_thread.start()
            self.last_frame = None

            self.second_thread_queue = Queue(maxsize=120)

            self.second_thread = threading.Thread(
                target=second_thread,
                args=(
                    self.second_thread_queue,
                    self.args.boot_int,
                    self.args.camId,
                    self.args.access_key,
                    self.args.secret_key,
                ),
            )
            self.second_thread.start()

            try:
                self.crowd_counter_enabled = self.args.counters_config.get(
                    "crowd_counter"
                ).get("enabled", False)
            except:
                self.crowd_counter_enabled = False
            try:
                self.zone_counter_enabled = self.args.counters_config.get(
                    "zone_counter"
                ).get("enabled", False)
            except:
                self.crowd_counter_enabled = False

            if not self.crowd_counter_enabled and not self.zone_counter_enabled:
                major_error(
                    self.args.camId,
                    "No tracker selected",
                    Exception("No tracker selected"),
                )
                return
            if self.crowd_counter_enabled and self.zone_counter_enabled:
                major_error(
                    self.args.camId,
                    "Only one tracker allowed",
                    Exception("Only one tracker allowed"),
                )
                return
        except Exception as e:
            tbe = traceback.TracebackException.from_exception(e)
            stack_frames = traceback.extract_stack()
            tbe.stack.extend(stack_frames)
            formatted_traceback = "".join(tbe.format())
            print(f"Formatted Traceback:\n{formatted_traceback}")
            print("raw err", e)
            major_error(self.args.camId, "Error in detection init", e)

    def log_to_console(self) -> None:
        if time.time() - self.last_console_log < 5:
            return
        logger.info(f"Detection, mean inference time: {self.inference_perf_mean}")
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.last_console_log = time.time()

    def handle_results(self, r: ultralytics.engine.results.Results, now: float):
        self.inference_perf_data.append(r.speed["inference"])
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.visualization_perf_mean = "{:.2f}".format(
            round(np.mean(self.inference_perf_data), 2)
        )  # type: ignore
        boxes: ultralytics.engine.results.Boxes = [
            d for d in (r.boxes if r.boxes is not None else []) if True
        ]  # Boxes object for bbox outputs
        self.counters.update(
            now, boxes, self.tracker.removed_stracks
        )  # type: ignore
        

    def start(self) -> Any:
        last_tracker_persist = 0.0
        while True:
            try:
                now_mono = time.monotonic()
                now = time.time()
                try:
                    (_, frame) = self.cam_thread.read()
                except:
                    time.sleep(0.1)
                    continue

                if self.results is None:
                    self.results = ultralytics.engine.results.Results(orig_img=frame, path="", names=self.names, speed={"preprocess": 0.0, "inference": 0.0, "loss": 0.0, "postprocess": 0.0})

                self.detect_bad_camera(frame)

                detection = self.model.predict(
                    frame,
                    conf=0.001,
                    vid_stride=3,
                    stream=False,
                    augment=False,
                    verbose=False,
                    classes=self.classes,
                    device=["mps"],
                )[0]


                det = detection.boxes.cpu().numpy()

                tracks = self.tracker.update(
                    det, detection.orig_img, getattr(detection, "feats", None)
                )

                self.results.update(boxes=torch.as_tensor(tracks)[:, :-1])

                r = self.results

                if self.maybe_close():
                    return

                # handle results
                self.handle_results(r, now)

                plot = self.counters.plot(
                    img=np.copy(frame),
                    boxes=r.boxes,
                    cam_ts=now,
                    labels=self.model.names,
                )

                self.second_thread_queue.put((frame, plot))

                if now - last_tracker_persist > 1.0:
                    save_tracker(self.tracker)
                    last_tracker_persist = now

                # throttle
                time.sleep(max(0.2 - (time.monotonic() - now_mono), 0.01))

                if self.maybe_close():
                    return
            except Exception as e:
                tbe = traceback.TracebackException.from_exception(e)
                stack_frames = traceback.extract_stack()
                tbe.stack.extend(stack_frames)
                formatted_traceback = "".join(tbe.format())
                print(f"Formatted Traceback:\n{formatted_traceback}")
                print("raw err", e)
                major_error(self.args.camId, "Error in detection loop", e)
                return

    def maybe_close(self):
        if self.server_stopped.is_set():
            try:
                self.cam_thread.stop()
                self.model.predictor.dataset.close()
            except:
                pass
            print("Detection stopped")
            return True

    def maybe_crash(self):
        self.errors = self.errors + 1

    def detect_bad_camera(self, frame):
        if self.last_frame is None:
            self.last_frame = frame
            return

        if fast_frame_comparison(frame, self.last_frame):
            self.freeze_frame_counter += 1
            print("Same frame !!!!")

        if self.freeze_frame_counter > 5:
            major_error(
                self.args.camId, "Camera freeze error", Exception("Camera freeze error")
            )
            return

        self.last_frame = frame


def fast_frame_comparison(img1, img2):
    if img1.shape != img2.shape:
        return False

    # For same shape, use efficient numpy operations
    difference = np.maximum(img1, img2) - np.minimum(img1, img2)
    return np.sum(difference) == 0

    # tracker_state = {}
    # if hasattr(model.predictor, 'trackers') and model.predictor.trackers:
    #     # Save the tracker's internal state
    #     for idx, tracker in enumerate(model.predictor.trackers):
    #         if tracker is not None:
    #             tracker_state[idx] = {
    #                 'frame_count': getattr(tracker, 'frame_count', 0),
    #                 'track_count': getattr(tracker, 'track_count_', 0)
    #             }

    # # Save to file
    # with open('manual_tracker_state.pkl', 'wb') as f:
    #     pickle.dump(tracker_state, f)
