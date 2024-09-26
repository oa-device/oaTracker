

from typing import Counter
import ultralytics.engine.results


class LineCrossingCounter(Counter):
    def __init__(self) -> None:
        super().__init__("line_crossing_counter")
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        pass
