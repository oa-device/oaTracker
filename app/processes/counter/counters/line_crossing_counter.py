

from typing import Counter
import ultralytics.engine.results


class LineCrossingCounter(Counter):
    def __init__(self) -> None:
        super().__init__("Line Crossing Counter")
    
    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        pass
