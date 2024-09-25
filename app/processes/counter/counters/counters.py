
import time
from typing import Any, Literal, TypedDict
import ultralytics.engine.results



class CounterTrackMeta(TypedDict):
    id: str

class Counter():
    def __init__(self, name:str) -> None:
        self.name = name
        self.data: list[Any] = []
        self.track_limit = 10_000
        self.meta = { "name": name, "track_limit": self.track_limit }
        self.last_cleanup = time.time()
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        pass
    
    def cleanup(self):
        if (time.time() - self.last_cleanup) < 1:
            return False

        if len(self.data) < self.track_limit:
            return False

        self.last_cleanup = time.time()

        return True

class Counters():
    def __init__(self, counters: list[Counter]) -> None:
        self.counters = counters
        self.data = {}
        self.meta = {}
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        data = {}
        meta = {}
        
        for counter in self.counters:
            counter.update(boxes)
            data[counter.name] = counter.data
            meta[counter.name] = counter.meta
            
        self.data = data
        self.meta = meta
        
