
from abc import ABC
from copy import deepcopy
import os
from pathlib import Path
from typing import Any
import ultralytics.engine.results
import ultralytics.trackers
from ultralytics.utils.plotting import Annotator
import datetime
from typing import Any
from uuid import uuid4
from app.utils.find import find

from app.parse_args import Args

database_folder_path = str(os.path.normpath(Path(__file__).parent / "../../db/"))

class Counter(ABC):
    def __init__(self, args: Args, name:str) -> None:
        self.name = name
        self.data: list[Any] = []
        self.track_limit = 10_000
        self.meta = { "name": name, "track_limit": self.track_limit }
        self.args = args
        self.counter_config: dict[str, Any]  =  self.args.counters_config["zone_counter"]
        
    
    def update(self, now: float, boxes: ultralytics.engine.results.Boxes, removed_stracks: list[Any]) -> None:
        pass
    
    def init(self, track_uuids: dict[int, bytes]) -> None:
        self.track_uuids = track_uuids
        
    def collect(self):
        return self.data, self.meta
    
    def get_label(self, id: int) -> str | None:
        return ""
    
    def plot(self, img: bytearray, boxes) -> bytearray:
        return img


class Counters():
    def __init__(self, args: Args, all_counters: list[type[Counter]]) -> None:
        self.data = {}
        self.meta = {}
        self.track_uuids = {}
        self.counters, self.classes = self.get_all_active_counters(args, all_counters)
            
        
    def get_all_active_counters(self, args: Args, all_counters: list[Counter]):
        all_active_counters=[]
        classes=[]
        active_counters_name =  args.counters_config.keys()
        for active_counter_name in active_counters_name:
            configs = [_counter for _counter in all_counters if active_counter_name == _counter.name]
            if len(configs) != 0:
                counter = configs[0](args)
                counter.init(self.track_uuids)
                all_active_counters.append(counter)
                classes += counter.classes
            
        return all_active_counters, classes

    
    def update(self,now: float, boxes: ultralytics.engine.results.Boxes, removed_stracks: list[Any]) -> None:
        data = {}
        meta = {}
        
        # add unique uuid to every track
        for box in boxes:
            id = int(box.id)
            if  id not in self.track_uuids:
                self.track_uuids[id] = uuid4().bytes
        
        for counter in self.counters:
            counter.update(now, boxes, removed_stracks)
            data[counter.name], meta[counter.name] = counter.collect()
            
        self.data = data
        self.meta = meta
        
   
    def plot(
        self,
        img: bytearray,
        boxes,
        cam_ts: float,
        labels: list[str],
    ):


        for counter in self.counters:
            counter.plot(img, boxes)

        annotator = Annotator(
            deepcopy(img),
            line_width=None,
            font_size=None,
            font="Arial.ttf",
            pil=False,
            example="",
        )

        # Plot Track results
        if boxes is not None:
            for t in boxes:
                d = t
                if d.id is None:
                    continue
                conf, id, cls = float(d.conf), int(d.id), int(d.cls)
            
                box_labels = self.get_labels(id)
                name = "" if id is None else f"id:{id} {labels[cls]}"
                label = f"{box_labels if len(box_labels) != 0 else ""} {int(conf * 100)}%" if conf else name
                annotator.box_label(d.xyxy[0], label, color=(0, 225, 27))

        annotator.text_label((1140,690,1280,720), datetime.datetime.fromtimestamp(cam_ts).strftime('%H:%M:%S'), color=(0,0,0))

        return annotator.result()
 
    def get_labels(self, id: int):
        labels: list[str | None] = []
        for counter in self.counters:
            labels.append(counter.get_label(id))
        
        return ", ".join(filter(None, labels))

    def collect(self):
        return self.data, self.meta        



