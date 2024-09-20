import time
from typing import Any


class PersonCounter:
    def __init__(self):
        self.movements_by_trackid = dict({})
        self.movements = []
        self.last_cleanup = time.time()
        self.track_limit = 500
        self.__count_since_boot = 0

    def update(self, boxes: list[Any]):
        now = time.time() * 1000

        for t in boxes:
            if t.conf[0] > 0.8:
                if t.id in self.movements_by_trackid:
                    self.movements_by_trackid[t.id][1] = now
                else:
                    self.__count_since_boot = self.__count_since_boot + 1
                    movements = [now, now, t.id]
                    self.movements.append(movements)
                    self.movements_by_trackid[t.id] = movements

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
                first_movement < to
                and latest_movement > _from
                and latest_movement - first_movement > 300
            ):
                count = count + 1

        self.cleanup()

        return count
