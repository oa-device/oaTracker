
import ultralytics.engine.results


class Counter():
    def __init__(self) -> None:
        pass
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        pass

class Counters():
    def __init__(self, counters: list[Counter]) -> None:
        self.counters = counters
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        for counter in self.counters:
            counter.update(boxes)
        
        
