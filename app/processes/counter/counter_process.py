import asyncio
import multiprocessing
import os
import time
import traceback
from typing import Any, NamedTuple

from app.config import TORCH_DEVICE, get_config,IMG_HEIGHT, IMG_WIDTH
from app.parse_args import Args
from app.processes.counter.counters.counters import Counters
from app.utils.logger import get_logger
from cv2 import imencode
import cv2
import numpy as np
from app.processes.counter.counters.person_counter import PersonCounter
from app.processes.counter.plot_results import plot

from ultralytics import YOLO

from app.ressources.video_capture_threading import VideoCaptureThreading

logger = get_logger(__name__)

"""

"""


counters = Counters([
    PersonCounter()
])


class Tracked(NamedTuple):
    xyxy: tuple[float,float,float,float]
    id: int
    conf: float
    label: str
    

class CounterProcess(multiprocessing.Process):
    def __init__(
        self,
        queue_all_events_output_counter: multiprocessing.Queue,
        queue_all_events_input_counter: multiprocessing.Queue,
        args: Args
    ):
        multiprocessing.Process.__init__(self, name=f"Counter")
        
        self.args = args
        
        self.queue_all_events_output_counter = queue_all_events_output_counter
        self.queue_all_events_input_counter = queue_all_events_input_counter

        self.must_broadcast = False

        self.cam_read_perf_data: list[float] = []
        self.cam_read_perf_mean = 0.0

        self.inference_perf_data: list[float] = []
        self.inference_perf_mean = 0.0

        self.visualization_perf_data: list[float] = []
        self.visualization_perf_mean = 0.0

        self.counters = counters
        self.tick = 0

        self.model = YOLO(f"{os.path.dirname(__file__)}/../../models/{self.args.model}", "track")
        
        config = get_config()
    
        self.classes = config["default_classes"]
        
        self.paused = False
        self.hide_overlay = False
        self.last_to = 0
        self.last_console_log = time.time() + 5
        self.errors = 0

    def run(self) -> None:
        asyncio.run(self.tracking_loop())

    def broadcast_dashboard(self, x: Any) -> None:
        if self.must_broadcast:
            self.queue_all_events_output_counter.put(x)

    def log_cam_read_perf(self, before_cam_read: float) -> None:
        if self.tick < 3:
            return

        after_cam_read = time.monotonic()
        cam_read_elapsed = (after_cam_read - before_cam_read) * 1000.0
        self.cam_read_perf_data.append(cam_read_elapsed)
        self.cam_read_perf_data = self.cam_read_perf_data[-10:]
        self.cam_read_perf_mean = "{:.2f}".format(round(np.mean(self.cam_read_perf_data), 2)) # type: ignore 

        self.broadcast_dashboard(
            {
                "event": f"cam_read_perf",
                "value": cam_read_elapsed,
                "mean": self.cam_read_perf_mean,
                "ts": time.time() * 1000,
            }
        )

    def log_result(self, results: Any, cam_ts: float) -> None:
        if self.tick < 3:
            return

        self.broadcast_dashboard(
            {
                "event": f"tracks",
                "results": results,
                "ts": time.time() * 1000,
                "frame_id": self.tick,
                "cam_ts": cam_ts
            }
        )

    def log_inference_perf(self, before_inference: float) -> None:
        if self.tick < 3:
            return

        after_inference = time.monotonic()
        inference_elapsed = (after_inference - before_inference) * 1000.0
        self.inference_perf_data.append(inference_elapsed)
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.inference_perf_mean = "{:.2f}".format(round(np.mean(self.inference_perf_data), 2)) # type: ignore 

        self.broadcast_dashboard(
            {
                "event": f"inference_perf",
                "value": inference_elapsed,
                "mean": self.inference_perf_mean,
                "ts": time.time() * 1000,
            }
        )

    def log_visualization_perf(self, before_visualization: float) -> None:
        if self.tick < 3:
            return

        after_visualization = time.monotonic()
        visualization_elapsed = (after_visualization - before_visualization) * 1000.0
        self.visualization_perf_data.append(visualization_elapsed)
        self.visualization_perf_data = self.visualization_perf_data[-10:]
        self.visualization_perf_mean = "{:.2f}".format(round(np.mean(self.visualization_perf_data), 2)) # type: ignore 

        self.broadcast_dashboard(
            {
                "event": f"visualization_perf",
                "value": visualization_elapsed,
                "mean": self.visualization_perf_mean,
                "ts": time.time() * 1000,
            }
        )

    def log_to_console(self) -> None:
        if time.time() - self.last_console_log < 5:
            return
        logger.info(
            f"Detection, mean inference time: {self.inference_perf_mean}"
        )
        self.last_console_log = time.time()

    def log_visualization(self, result: Any, cam_ts: float) -> None:
        before_visualization = time.monotonic()
        frame = (result.orig_img
                    if self.hide_overlay
                    else plot(
                        img=result.orig_img,
                        boxes=result.boxes,
                        cam_ts=cam_ts,
                        labels=self.model.names
                    ))
        output_frame = frame.copy()
        _, img = imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if _:
            self.broadcast_dashboard(
                {
                    "event": f"visualization",
                    "value": bytearray(img),
                    "ts": time.time() * 1000,
                    "cam_ts": cam_ts
                }
            )

        self.log_visualization_perf(before_visualization)

    """
    
    """

    async def handle_events(self) -> None:
        once = True
        event = None
        while event or once:
            once = False
            await asyncio.sleep(0.01)
            try:
                event = self.queue_all_events_input_counter.get_nowait()
            except:
                break
            if event:
                self.handle_event(event)

    def handle_event(self, event):
        if event["event"] == "get_count":
            count = self.counter.get_count(event["from"], event["to"])
            self.last_to = event["to"]
            self.queue_all_events_output_counter.put(
                {
                    "event": f"count",
                    "count": count,
                    "id": event["id"],
                }
            )
        elif event["event"] == "set_dashboard":
            self.must_broadcast = event["value"]
        elif event["event"] == "set_paused":
            self.paused = event["value"]
        elif event["event"] == "set_hide_overlay":
            self.hide_overlay = event["value"]
        elif event["event"] == "get_count_for_dashboard":
            count = self.counter.get_count(event["from"], event["to"])
            count_since_boot = self.counter.get_count_since_boot()
            self.broadcast_dashboard(
                {
                    "event": f"count_for_dashboard",
                    "count": count,
                    "count_since_boot": count_since_boot,
                }
            )

    async def tracking_loop(self) -> Any:
        cam = VideoCaptureThreading(
            width=IMG_WIDTH,
            height=IMG_HEIGHT,
        )
        cam.start()
        
        while True:
            now = time.monotonic()
            now_ts = time.time() * 1000
            handle_events_coroutine = self.handle_events()
            try:
                await handle_events_coroutine

                if self.paused:
                    continue

                self.tick = self.tick + 1
                before_cam_read = time.monotonic()
                grabbed, frame = cam.read()
                self.log_cam_read_perf(before_cam_read)

                if grabbed:
                    before_inference = time.monotonic()

                    result = self.model.track(
                        tracker=f"{os.path.dirname(__file__)}/botsort_custom.yaml",
                        source=frame,
                        persist=True,
                        imgsz=IMG_WIDTH,
                        conf=0.02,
                        #classes=self.classes,
                        iou=0.6,
                        verbose=False,
                        device=TORCH_DEVICE
                    )
                else:
                    self.maybe_crash()
                    raise Exception(f"No data from device")

                self.log_inference_perf(before_inference)
                
                boxes = result[0].boxes
                
                # handle results
                if boxes is not None:
                    self.counters.update(boxes)
                    
                    self.log_result(list(map(self.format_tracked, boxes)), now_ts)
                else:
                    self.counters.update([])
                    self.log_result([], now_ts)

                self.log_visualization(result[0], now_ts)
            except Exception as error:
                print(traceback.format_exc())
                logger.error(error)
                pass

            wait_time = max(0.01, 0.1 - (time.monotonic() - now) / 1000)
            self.log_to_console()
            await asyncio.sleep(wait_time)

    def format_tracked(self, t):
        val = t.xyxy

        return Tracked((float(val[0][0]), float(val[0][1]), float(val[0][0] + val[0][2]), float(val[0][1] + val[0][3])), int(t.id), float(t.conf), self.model.names[int(t.cls)])



    def maybe_crash(self):
        self.errors = self.errors + 1
        if self.errors > 10:
            self.queue_all_events_output_counter.put({"event": "crash"})


def start_counter_process(
    queue_all_events_output_counter: multiprocessing.Queue,
    queue_all_events_input_counter: multiprocessing.Queue,
    args: Args
):
    CounterProcess(
        queue_all_events_output_counter,
        queue_all_events_input_counter,
        args
    ).start()


