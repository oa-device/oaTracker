import time
from typing import Any


from app.processes.counter.counters.counters import Counter
import ultralytics.engine.results

from app.utils.logger import create_log_message, get_logger



logger=get_logger(__name__)

class GenericCounter(Counter):
    def __init__(self, name:str, cls: int):
        super().__init__(name)
        self.cls = cls
        # [first_seen, last_seen, id, frame_count]
        self.data_by_trackid: dict[int, list[float | int]] = dict({})
        self.data: list[list[float | int]] = []
        self.last_cleanup = time.time()
        self.track_limit = 10_000
        self.__count_since_boot = 0

    def update(self, boxes: ultralytics.engine.results.Boxes) -> None:
        now = time.time()
        for t in boxes:
            try:
                if t.is_track and int(t.cls) == self.cls and float(t.conf) > 0.8:
                    id = int(t.id) # type: ignore
                    if  id in self.data_by_trackid:
                        self.data_by_trackid[id][1] = now
                        self.data_by_trackid[id][3] += 1
                    else:
                        self.__count_since_boot = self.__count_since_boot + 1
                        data = [now, now, id, 1]
                        self.data.append(data)
                        self.data_by_trackid[id] = data
            except:
                print('this weird box', t)

    def cleanup(self):
        should_clean = super().cleanup()
        
        if not should_clean:
            return
        
        self.data = sorted(self.data, key=lambda x: x[1], reverse=True)[
            : self.track_limit
        ]
        self.data_by_trackid = dict(
            zip([x[2] for x in self.data], self.data)
        )


    def is_counted(self, x, _from: float, to: float):
        if x not in self.data_by_trackid:
            return False

        first_movement, last_seen, _ = self.data_by_trackid[x]
        if (
            first_movement < to
            and last_seen > _from
            and last_seen - first_movement > 300
        ):
            return True

        return False


    def get_count_since_boot(self) -> int:
        return self.__count_since_boot


    def get_count(self, _from: float, to: float):
        count = 0

        for x in self.data:
            first_seen, last_seen, _ = x
            if (
                first_seen < (to / 1000)
                and last_seen > (_from / 1000)
                and last_seen - first_seen > 300
            ):
                count = count + 1

        self.cleanup()
        
        logger.info(
            create_log_message(
                event="person_counter_get_count",
                count=count,
                from_ms=_from,
                to_ms=to,
                total_tracks=len(self.data),
            )
        )

        return count
