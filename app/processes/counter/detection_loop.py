import mmap
import os
import time
import traceback
from typing import Any, NamedTuple

import ultralytics.engine.results

from app.counters import Counters
from app.parse_args import Args
from app.processes.counter.video_capture_threading import VideoCaptureThreading
from app.utils.logger import get_logger
from cv2 import imencode
import cv2
import numpy as np

from multiprocessing.synchronize import Event as EventClass
from ultralytics import YOLOE

from app.utils.mmap import mmap_context, mmap_write, pathname_img
from app.utils.stop_detection import major_error
logger = get_logger(__name__)


class Tracked(NamedTuple):
    xyxy: tuple[float, float, float, float]
    id: int
    conf: float
    label: str


def byte_size(s):
    return len(s.encode("utf-8"))


class CounterLoop:

    def __init__(self, args: Args, all_counters, server_stopped: EventClass):
        self.running = True
        self.args = args

        self.fps = 0.0

        self.inference_perf_data: list[float] = []
        self.inference_perf_mean = 0.0

        self.tick = 0

        self.model = YOLOE(
            f"{os.path.dirname(__file__)}/../../../models/{self.args.model}", "track"
        )

        self.counters = Counters(args, all_counters)

        self.classes = self.counters.classes
        
        print(self.classes)
        
        self.model.set_classes(self.classes, self.model.get_text_pe(self.classes))

        self.last_console_log = time.time() + 5
        self.errors = 0
        self.freeze_frame_counter = 0

        self.log: dict[str, Any] = {}
        self.server_stopped = server_stopped
        self.cam_thread = VideoCaptureThreading()
        self.cam_thread.start()
        self.last_frame = None
        
        try:
            self.crowd_counter_enabled = self.args.counters_config.get('crowd_counter').get('enabled', False)
        except:
            self.crowd_counter_enabled = False
        try:
            self.zone_counter_enabled = self.args.counters_config.get('zone_counter').get('enabled', False)
        except:
            self.crowd_counter_enabled = False
        
        if not self.crowd_counter_enabled and not self.zone_counter_enabled:
            major_error("No tracker selected", Exception("No tracker selected"))
        if self.crowd_counter_enabled and self.zone_counter_enabled:
            major_error("Only one tracker allowed", Exception("Only one tracker allowed"))
            
    def log_to_console(self) -> None:
        if time.time() - self.last_console_log < 5:
            return
        logger.info(f"Detection, mean inference time: {self.inference_perf_mean}")
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.last_console_log = time.time()

    def log_visualization(
        self,
        frame,
        result: ultralytics.engine.results.Results,
        cam_ts: float,
        shared_memory_img: mmap.mmap,
    ) -> None:
        try:
            frame = self.counters.plot(
                img=frame,
                boxes=result.boxes,
                cam_ts=cam_ts,
                labels=self.model.names,
            )
            _, img = imencode(".webp", frame, [int(cv2.IMWRITE_WEBP_QUALITY), 20])
            if _:
                mmap_write(shared_memory_img, 512000, img.tobytes())
        except:
            print('logging viz error')

    def handle_results(self, r: ultralytics.engine.results.Results, now: float):
        # print(now, r.speed)
        self.inference_perf_data.append(r.speed["inference"])
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.visualization_perf_mean = "{:.2f}".format(round(np.mean(self.inference_perf_data), 2))  # type: ignore
        boxes: ultralytics.engine.results.Boxes = [
            d for d in (r.boxes if r.boxes is not None else []) if d.is_track
        ]  # Boxes object for bbox outputs
        self.counters.update(now, boxes, self.model.predictor.trackers[0].removed_stracks)  # type: ignore

    def start(self) -> Any:
        with mmap_context(pathname_img, 512000) as shared_memory_img:

            if self.maybe_close():
                return

            try:
                while True:
                    try:
                        now = time.time()
                        (_, frame) = self.cam_thread.read()
                        
                        self.detect_bad_camera(frame)
                        
                        r = self.model.track(
                            frame,
                            imgsz=736,
                            tracker=f"{os.path.dirname(__file__)}/botsort_custom.yaml",
                            persist=True,
                            conf=0.001,
                            vid_stride=2,
                            iou=0.4,
                            stream=False,
                            augment=False,
                            verbose=False,
                            device="mps",
                        )[0]

                        if self.maybe_close():
                            return

                        # handle results
                        self.handle_results(r, now)
                        self.log_visualization(frame, r, now, shared_memory_img)

                        if self.maybe_close():
                            return
                    except Exception as e:
                        
                        tbe = traceback.TracebackException.from_exception(e)
                        stack_frames = traceback.extract_stack()
                        tbe.stack.extend(stack_frames)
                        formatted_traceback = "".join(tbe.format())
                        print(f"Formatted Traceback:\n{formatted_traceback}")
                        print(111, e)
            except ConnectionError as e:
                major_error("Camera connection error", e)
            except Exception as e:
                major_error("Error in detection loop", e)

    def maybe_close(self):
        if self.server_stopped.is_set():
            try:
                self.cam_thread.stop()
                self.model.predictor.dataset.close()
            except:
                pass
            print("Detection stopped")
            return True

    def format_tracked(self, t):
        val = t.xyxy

        return Tracked(
            (
                float(val[0][0]),
                float(val[0][1]),
                float(val[0][0] + val[0][2]),
                float(val[0][1] + val[0][3]),
            ),
            int(t.id),
            float(t.conf),
            self.model.names[int(t.cls)],
        )

    def maybe_crash(self):
        self.errors = self.errors + 1
        
    def detect_bad_camera(self, frame):
        if self.last_frame is None:
            self.last_frame = frame
            return
        
        if fast_frame_comparison(frame, self.last_frame):
            self.freeze_frame_counter += 1
            print('Same frame !!!!')
        
        
        if self.freeze_frame_counter > 5:
            major_error("Camera freeze error", Exception("Camera freeze error"))
            return
            
        self.last_frame = frame

def fast_frame_comparison(img1, img2):
    if img1.shape != img2.shape:
        return False
    
    # For same shape, use efficient numpy operations
    difference = np.maximum(img1, img2) - np.minimum(img1, img2)
    return np.sum(difference) == 0