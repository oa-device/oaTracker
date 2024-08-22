import time
from src.utils.logger import get_logger, create_log_message

logger = get_logger(__name__)


class PersonCounter:
    counters = {}

    @classmethod
    def get_counter(cls, device_id=None):
        if device_id is None:
            # If no specific device_id is provided, return the first (and possibly only) counter
            return next(iter(cls.counters.values())) if cls.counters else None
        if device_id not in cls.counters:
            cls.counters[device_id] = PersonCounter(device_id)
            logger.info(create_log_message(event="person_counter_created", device_id=device_id))
        return cls.counters[device_id]

    def __init__(self, device_id):
        self.device_id = device_id
        self.movements_by_trackid = {}
        self.movements = []
        self.last_cleanup = time.time() * 1000
        self.track_limit = 500
        self.__count_since_boot = 0
        logger.info(create_log_message(event="person_counter_init", device_id=device_id))

    def update(self, tracked_objects):
        now = int(time.time() * 1000)
        updated_count = 0
        for obj in tracked_objects:
            if obj["id"] is not None and obj["label"] == "person":
                if obj["id"] in self.movements_by_trackid:
                    self.movements_by_trackid[obj["id"]][1] = now
                else:
                    self.__count_since_boot += 1
                    updated_count += 1
                    movements = [now, now, obj["id"]]
                    self.movements.append(movements)
                    self.movements_by_trackid[obj["id"]] = movements
        logger.debug(
            create_log_message(
                event="person_counter_update", device_id=self.device_id, updated_count=updated_count, total_count=self.__count_since_boot
            )
        )

    def get_count(self, from_seconds, to_seconds):
        from_ms = int(from_seconds * 1000)
        to_ms = int(to_seconds * 1000)
        count = 0
        for first_movement, latest_movement, _ in self.movements:
            if first_movement <= to_ms and latest_movement >= from_ms:
                count += 1
        self.cleanup()
        logger.info(
            create_log_message(
                event="person_counter_get_count",
                device_id=self.device_id,
                count=count,
                from_ms=from_ms,
                to_ms=to_ms,
                total_movements=len(self.movements),
            )
        )
        return count

    def cleanup(self):
        now = int(time.time() * 1000)
        if now - self.last_cleanup < 1000 or len(self.movements) < self.track_limit:
            return
        self.last_cleanup = now
        self.movements = sorted(self.movements, key=lambda x: x[1], reverse=True)[: self.track_limit]
        self.movements_by_trackid = {x[2]: x for x in self.movements}

    def get_count_since_boot(self):
        return self.__count_since_boot
