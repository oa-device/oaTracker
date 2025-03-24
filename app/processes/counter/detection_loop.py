import mmap
import os
import time
from typing import Any, NamedTuple

import ultralytics.engine.model
import ultralytics.engine.predictor
import ultralytics.engine.results
import ultralytics.trackers

from app.counters import Counters
from app.parse_args import Args
from app.utils.logger import get_logger
from cv2 import imencode, resize
import cv2
import numpy as np

from multiprocessing.synchronize import Event as EventClass
from ultralytics import YOLO

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

        self.model = YOLO(
            f"{os.path.dirname(__file__)}/../../../models/{self.args.model}", "track"
        )

        self.counters = Counters(args, all_counters)

        self.classes = self.counters.classes

        self.last_console_log = time.time() + 5
        self.errors = 0

        self.log: dict[str, Any] = {}
        self.server_stopped = server_stopped

    def log_to_console(self) -> None:
        if time.time() - self.last_console_log < 5:
            return
        logger.info(f"Detection, mean inference time: {self.inference_perf_mean}")
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.last_console_log = time.time()

    def log_visualization(
        self,
        result: ultralytics.engine.results.Results,
        cam_ts: float,
        shared_memory_img: mmap.mmap,
    ) -> None:
        frame = self.counters.plot(
            img=result.orig_img,
            boxes=result.boxes,
            cam_ts=cam_ts,
            labels=self.model.names,
        )
        im = resize(frame, (640, 360))
        _, img = imencode(".webp", im, [int(cv2.IMWRITE_WEBP_QUALITY), 20])
        if _:
            mmap_write(shared_memory_img, 512000, img.tobytes())

    def handle_results(self, r: ultralytics.engine.results.Results, now: float):
        # print(now, r.speed)
        self.inference_perf_data.append(r.speed["inference"])
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.visualization_perf_mean = "{:.2f}".format(round(np.mean(self.inference_perf_data), 2))  # type: ignore
        boxes: ultralytics.engine.results.Boxes = [
            d for d in (r.boxes if r.boxes is not None else []) if d.is_track
        ]  # Boxes object for bbox outputs
        self.counters.update(now, boxes, self.model.predictor.trackers[0].removed_stracks)  # type: ignore
        print(self.visualization_perf_mean)

    def start(self) -> Any:
        with mmap_context(pathname_img, 512000) as shared_memory_img:

            if self.maybe_close():
                return
            
            cap = cv2.VideoCapture(self.args.yolo_source)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            try:
                while True:
                    try:
                        now = time.time()
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                        
                        r = self.model.track(
                            frame,
                            tracker=f"{os.path.dirname(__file__)}/botsort_custom.yaml",
                            persist=True,
                            conf=0.001,
                            vid_stride=1,
                            classes=self.classes,
                            iou=0.4,
                            augment=False,
                            verbose=False,
                            device="mps",
                        )[0]

                        if self.maybe_close():
                            return

                        # handle results
                        self.handle_results(r, now)
                        self.log_visualization(r, now, shared_memory_img)

                        if self.maybe_close():
                            return
                    except Exception as e:
                        print(111, e)
            except ConnectionError as e:
                major_error("Camera connection error", e)
            except Exception as e:
                print(222, e)

    def maybe_close(self):
        if self.server_stopped.is_set():
            try:
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
