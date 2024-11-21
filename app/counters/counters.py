
from abc import ABC
from copy import deepcopy
from functools import reduce
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Union
import uuid
import ultralytics.engine.results
import ultralytics.trackers
from ultralytics.utils.plotting import Annotator
import datetime
from typing import Any
from uuid import uuid4
from app.utils.find import find

from app.parse_args import Args
from pyiceberg.catalog import load_catalog

database_folder_path = str(os.path.normpath(Path(__file__).parent / "../../db/"))



class Counter(ABC):
    def __init__(self, args: Args, name:str) -> None:
        self.name = name
        self.data: list[Any] = []
        self.track_limit = 10_000
        self.meta = { "name": name, "track_limit": self.track_limit }
        self.args = args
        print(self.args.counters_config)
        counter_config = find(lambda counter_config: counter_config["name"] == name, self.args.counters_config) # type: ignore
        self.counter_config: dict[str, Any]  =  counter_config["config"] if "config" in counter_config else dict()
        
    
    def update(self, now: float, boxes: ultralytics.engine.results.Boxes, tracker: ultralytics.trackers.bot_sort.BOTSORT) -> None:
        pass
    
    def init(self, connection: sqlite3.Connection, track_uuids: dict[int, bytes]) -> None:
        self.connection = connection

        self.track_uuids = track_uuids
        
    def collect(self):
        return self.data, self.meta
    
    def get_label(self, id: int) -> str | None:
        return ""
    
    def plot(self, img: bytearray) -> bytearray:
        return img


class Counters():
    def __init__(self, args: Args, all_counters: list[type[Counter]]) -> None:
        self.data = {}
        self.meta = {}
        self.track_uuids = {}
        self.connection = sqlite3.connect(database_folder_path + "/cam1.db")
        self.counters, self.classes = self.get_all_active_counters(args, all_counters)
            
        
    def get_all_active_counters(self, args: Args, all_counters: list[Counter]):
        all_active_counters=[]
        classes=[]
        active_counters_name =  list(map(lambda counter_config: counter_config["name"], args.counters_config))
        for active_counter_name in active_counters_name:
            configs = [_counter for _counter in all_counters if active_counter_name == _counter.name]
            if len(configs) != 0:
                counter = configs[0](args)
                counter.init(self.connection, self.track_uuids)
                all_active_counters.append(counter)
                classes += counter.classes
            
        return all_active_counters, classes

    
    def update(self,now: float, boxes: ultralytics.engine.results.Boxes, tracker: ultralytics.trackers.bot_sort.BOTSORT) -> None:
        data = {}
        meta = {}
        
        # add unique uuid to every track
        for box in boxes:
            id = int(box.id)
            if  id not in self.track_uuids:
                self.track_uuids[id] = uuid4().bytes
        
        for counter in self.counters:
            counter.update(now, boxes, tracker)
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
            counter.plot(img)

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
                label = f"{name}{" " + box_labels if len(box_labels) != 0 else ""} {int(conf * 100)}%" if conf else name
                annotator.box_label(d.xyxy[0], label, color=(0, 225, 27))

        annotator.text_label((544,460,640,480), datetime.datetime.fromtimestamp(cam_ts/1000).strftime('%H:%M:%S'), color=(0,0,0))

        return annotator.result()
 
    def get_labels(self, id: int):
        labels: list[str | None] = []
        for counter in self.counters:
            labels.append(counter.get_label(id))
        
        return ", ".join(filter(None, labels))

    def collect(self):
        return self.data, self.meta        



