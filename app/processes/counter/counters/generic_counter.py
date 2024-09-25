import time
from typing import Any


from app.processes.counter.counters.counters import Counter
import ultralytics.engine.results



class GenericCounter(Counter):
    def __init__(self, cls: int):
        self.cls = cls
        self.name = f"Generic counter class {cls}"
        self.movements_by_trackid: dict[int, list[float | int]] = dict({})
        self.movements: list[list[float | int]] = []
        self.last_cleanup = time.time()
        self.track_limit = 10_000
        self.__count_since_boot = 0

    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        now = time.time()

        for t in boxes:
            id = int(t.id) # type: ignore
            if int(t.cls) == self.cls and float(t.conf) > 0.8:
                if  id in self.movements_by_trackid:
                    self.movements_by_trackid[id][1] = now
                else:
                    self.__count_since_boot = self.__count_since_boot + 1
                    movements = [now, now, id]
                    self.movements.append(movements)
                    self.movements_by_trackid[id] = movements

    def is_counted(self, x, _from: float, to: float):
        if x not in self.movements_by_trackid:
            return False

        first_movement, latest_movement, _ = self.movements_by_trackid[x]
        if (
            first_movement < to
            and latest_movement > _from
            and latest_movement - first_movement > 300
        ):
            return True

        return False

    def cleanup(self):
        if (time.time() - self.last_cleanup) < 1:
            return

        if len(self.movements) < self.track_limit:
            return

        self.last_cleanup = time.time()

        self.movements = sorted(self.movements, key=lambda x: x[1], reverse=True)[
            : self.track_limit
        ]
        self.movements_by_trackid = dict(
            zip([x[2] for x in self.movements], self.movements)
        )

        return

    def get_count_since_boot(self) -> int:
        return self.__count_since_boot

    def get_count(self, _from: float, to: float):
        count = 0

        for x in self.movements:
            first_movement, latest_movement, _ = x
            if (
                first_movement < (to / 1000)
                and latest_movement > (_from / 1000)
                and latest_movement - first_movement > 300
            ):
                count = count + 1

        self.cleanup()

        return count
