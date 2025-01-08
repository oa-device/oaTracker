import asyncio
import json
import mmap
import multiprocessing
import os
import time
import traceback
from typing import Any, NamedTuple

import ultralytics.engine.model
import ultralytics.engine.predictor
import ultralytics.engine.results
import ultralytics.trackers

from app.config import TORCH_DEVICE, get_config,IMG_HEIGHT, IMG_WIDTH
from app.counters import Counters
from app.utils.logger import get_logger
from cv2 import imencode, resize
import cv2
import numpy as np
#from app.counters import PersonCounter

from ultralytics import YOLO

from app.utils.mmap import mmap_context, mmap_write, pathname_state, pathname_img

logger = get_logger(__name__)


class Tracked(NamedTuple):
    xyxy: tuple[float,float,float,float]
    id: int
    conf: float
    label: str
    
def byte_size(s):
    return len(s.encode('utf-8'))

class CounterLoop():
            
    def __init__(self, args, all_counters):
        self.running = True
        self.args = args
        
        self.fps = 0.0

        self.inference_perf_data: list[float] = []
        self.inference_perf_mean = 0.0

        self.tick = 0

        self.model = YOLO(f"{os.path.dirname(__file__)}/../../../models/{self.args.model}", "track")
    
        self.counters = Counters(args, all_counters)
        
        self.classes = self.counters.classes
        
        self.last_console_log = time.time() + 5
        self.errors = 0
        
        self.log: dict[str, Any]={}
        

    def log_to_console(self) -> None:
        if time.time() - self.last_console_log < 5:
            return
        logger.info(
            f"Detection, mean inference time: {self.inference_perf_mean}"
        )
        self.inference_perf_data = self.inference_perf_data[-10:]
        self.last_console_log = time.time()

    def log_visualization(self, result: Any, cam_ts: float, shared_memory_img: mmap.mmap) -> None:
        frame = (self.counters.plot(
                        img=result.orig_img,
                        boxes=result.boxes,
                        cam_ts=cam_ts,
                        labels=self.model.names
                    ))
        im=resize(frame, (640,360))
        _, img = imencode(".jpeg", im, [int(cv2.IMWRITE_JPEG_QUALITY), 13])
        if _:
            mmap_write(shared_memory_img, 512000, img.tobytes())

    
    def logs_to_mmap(self, shared_memory_state:mmap.mmap):
        data=json.dumps(self.log).encode('utf-8')
        mmap_write(shared_memory_state, 512000, data)

    def start(self) -> Any:
        with (mmap_context(pathname_img, 512000) as shared_memory_img,
                mmap_context(pathname_state, 512000) as shared_memory_state):
        
            batch = 3
            # visualization_perf_data=[11]
        
            generator = self.model.track(
                tracker=f"{os.path.dirname(__file__)}/botsort_custom.yaml",
                source="0",
                stream=True,
                persist=True,
                batch=batch,
                imgsz=1280,
                conf=0.02,
                #vid_stride=3,
                classes=self.classes,
                iou=0.6,
                augment=True,
                verbose=False,
                device='cuda'
            )
            
            for r in generator:
                self.inference_perf_data.append(r.speed["inference"])
                self.inference_perf_data = self.inference_perf_data[-10:]
                self.visualization_perf_mean = "{:.2f}".format(round(np.mean(self.inference_perf_data), 2)) # type: ignore 
                now = time.time()
                boxes: ultralytics.engine.results.Boxes = [d for d in (r.boxes if r.boxes is not None else []) if d.is_track]  # Boxes object for bbox outputs
                self.counters.update(now, boxes, self.model.predictor.trackers[0]) # type: ignore
                # print(visualization_perf_mean)
                
                # handle results
                self.log_visualization(r, now * 1000, shared_memory_img)
                self.logs_to_mmap(shared_memory_state)

    def format_tracked(self, t):
        val = t.xyxy

        return Tracked((float(val[0][0]), float(val[0][1]), float(val[0][0] + val[0][2]), float(val[0][1] + val[0][3])), int(t.id), float(t.conf), self.model.names[int(t.cls)])

    def maybe_crash(self):
        self.errors = self.errors + 1
