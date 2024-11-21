import asyncio
import json
import mmap
import multiprocessing
import os
import time
import traceback
from typing import Any, NamedTuple

from app.counters.counters import Counter
import ultralytics.engine.model
import ultralytics.engine.predictor
import ultralytics.engine.results
import ultralytics.trackers

from app.config import TORCH_DEVICE, get_config,IMG_HEIGHT, IMG_WIDTH
from app.counters import ZoneCounter
from app.parse_args import Args
from app.counters import Counters
from app.utils.logger import get_logger
from cv2 import imencode
import cv2
import numpy as np
#from app.counters import PersonCounter

from ultralytics import YOLO

from app.processes.counter.video_capture_threading import VideoCaptureThreading
from app.utils.mmap import mmap_context, mmap_write, pathname_state, pathname_img

logger = get_logger(__name__)


from app.counters.zone_counter import ZoneCounter
from app.counters.person_counter import PersonCounter


class Tracked(NamedTuple):
    xyxy: tuple[float,float,float,float]
    id: int
    conf: float
    label: str
    
def byte_size(s):
    return len(s.encode('utf-8'))

class CounterLoop():
            
    def __init__(self, args, queue_all_events_input_counter, all_counters):
        self.running = True
        self.args = args
        
        self.fps = 0.0
        
        self.queue_all_events_input_counter = queue_all_events_input_counter

        self.must_broadcast = False
        
        self.cam_read_perf_data: list[float] = []
        self.cam_read_perf_mean = 0.0

        self.inference_perf_data: list[float] = []
        self.inference_perf_mean = 0.0

        self.visualization_perf_data: list[float] = []
        self.visualization_perf_mean = 0.0
        
        self.full_perf_data: list[float] = []
        self.full_perf_mean = 0.0
        self.full_perf_last_update = time.monotonic()

        self.tick = 0

        self.model = YOLO(f"{os.path.dirname(__file__)}/../../../models/{self.args.model}", "track")
    
        self.counters = Counters(args, all_counters)
        
        self.classes = self.counters.classes
        
        self.paused = False
        self.hide_overlay = False
        self.last_to = 0
        self.last_console_log = time.time() + 5
        self.errors = 0
        
        self.log: dict[str, Any]={}
        

    def broadcast_dashboard(self, x: Any) -> None:
        event_name=x["event"]
        x.pop("event", None)
        self.log[event_name] = x

    def log_cam_read_perf(self, before_cam_read: float) -> None:
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

    def log_result(self, boxes: Any, cam_ts: float) -> None:
        now = time.monotonic()
        diff = now - self.full_perf_last_update
        self.full_perf_data.append(diff)
        self.full_perf_last_update = now
        self.full_perf_data = self.full_perf_data[-10:]
        mean = np.mean(self.full_perf_data)
        self.full_perf_mean = "{:.2f}".format(round(mean, 2)) # type: ignore 

        self.fps = 1.0 / mean
        
        data, meta = self.counters.collect()
        
        self.broadcast_dashboard(
            {
                "event": f"tracks",
                "boxes": boxes,
                "ts": time.time() * 1000,
                "frame_id": self.tick,
                "cam_ts": cam_ts * 1000,
                "fps": self.fps,
                "counters_meta": meta,
                "counters_data": data
            }
        )

    def log_inference_perf(self, before_inference: float) -> None:
        after_inference = time.monotonic()
        inference_elapsed = (after_inference - before_inference) * 1000.0
        self.inference_perf_data.append(inference_elapsed)
        self.inference_perf_mean = "{:.2f}".format(round(np.mean(self.inference_perf_data), 2)) # type: ignore 
        self.inference_perf_95 = "{:.2f}".format(round(np.percentile(self.inference_perf_data, 95, method="lower"), 2)) # type: ignore 

        self.broadcast_dashboard(
            {
                "event": f"inference_perf",
                "value": inference_elapsed,
                "mean": self.inference_perf_mean,
                "ts": time.time() * 1000,
            }
        )

    def log_visualization_perf(self, before_visualization: float) -> None:
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
            f"Detection, mean inference time: {self.inference_perf_95}"
        )
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.last_console_log = time.time()

    def log_visualization(self, result: Any, cam_ts: float, shared_memory_img: mmap.mmap) -> None:
        before_visualization = time.monotonic()
        if self.must_broadcast:
            frame = (result.orig_img
                        if self.hide_overlay
                        else self.counters.plot(
                            img=result.orig_img,
                            boxes=result.boxes,
                            cam_ts=cam_ts,
                            labels=self.model.names
                        ))
            _, img = imencode(".jpeg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 15])
            if _:
                mmap_write(shared_memory_img, 64000, img.tobytes())

        self.log_visualization_perf(before_visualization)

    async def handle_events(self) -> None:
        once = True
        event = None
        while event or once:
            once = False
            await asyncio.sleep(0.0001)
            try:
                event = self.queue_all_events_input_counter.get_nowait()
            except Exception:
                break
            if event:
                self.handle_event(event)

    def handle_event(self, event):
        if event["event"] == "get_count":
            pass
            # count = self.counter.get_count(event["from"], event["to"])
            # self.last_to = event["to"]
            # self.queue_all_events_output_counter.put(
            #     {
            #         "event": f"count",
            #         "count": count,
            #         "id": event["id"],
            #     }
            # )
        elif event["event"] == "set_dashboard":
            self.must_broadcast = event["value"]
        elif event["event"] == "set_paused":
            self.paused = event["value"]
        elif event["event"] == "set_hide_overlay":
            self.hide_overlay = event["value"]
        elif event["event"] == "get_count_for_dashboard":
            pass
            # count = self.counter.get_count(event["from"], event["to"])
            # count_since_boot = self.counter.get_count_since_boot()
            # self.broadcast_dashboard(
            #     {
            #         "event": f"count_for_dashboard",
            #         "count": count,
            #         "count_since_boot": count_since_boot,
            #     }
            # )


    
    def logs_to_mmap(self, shared_memory_state:mmap.mmap):
        data=json.dumps(self.log).encode('utf-8')
        mmap_write(shared_memory_state, 64000, data)

    async def tracking_loop(self) -> Any:
        with (mmap_context(pathname_img, 64000) as shared_memory_img,
                mmap_context(pathname_state, 64000) as shared_memory_state):
            
            
            while self.running:
                try:
                    cam = VideoCaptureThreading(
                        width=IMG_WIDTH,
                        height=IMG_HEIGHT,
                    )
                    cam.start()
                    break
                except Exception as error:
                    print(traceback.format_exc())
                    logger.error(error)
                    pass
            
            while self.running:
                
                now = time.time()
                handle_events_coroutine = self.handle_events()
                try:
                    await handle_events_coroutine

                    if self.paused:
                        print('paused')
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
                            classes=self.classes,
                            iou=0.6,
                            verbose=False,
                            device=TORCH_DEVICE
                        )
                    else:
                        self.maybe_crash()
                        raise Exception(f"No data from device")
                    
                    self.log_inference_perf(before_inference)
                    
                    boxes: ultralytics.engine.results.Boxes =  [d for d in (result[0].boxes if result[0].boxes is not None else []) if d.is_track] # type: ignore 
                    self.counters.update(now, boxes, self.model.predictor.trackers[0]) # type: ignore
                    
                    # handle results
                    self.log_visualization(result[0], now * 1000, shared_memory_img)
                    self.log_result(list(map(self.format_tracked, boxes)), now * 1000)
                    self.logs_to_mmap(shared_memory_state)
                    
                except Exception as error:
                    print(traceback.format_exc())
                    logger.error(error)
                    pass

                self.log_to_console()

            if cam:
                cam.stop()
            print('Counter stopped')

    def format_tracked(self, t):
        val = t.xyxy

        return Tracked((float(val[0][0]), float(val[0][1]), float(val[0][0] + val[0][2]), float(val[0][1] + val[0][3])), int(t.id), float(t.conf), self.model.names[int(t.cls)])


    def maybe_crash(self):
        self.errors = self.errors + 1
