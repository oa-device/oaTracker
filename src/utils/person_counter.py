import time


class PersonCounter:
    counters = {}

    @classmethod
    def get_counter(cls, device_id):
        if device_id not in cls.counters:
            cls.counters[device_id] = PersonCounter(device_id)
        return cls.counters[device_id]

    def __init__(self, device_id):
        self.device_id = device_id
        self.movements_by_trackid = {}
        self.movements = []
        self.last_cleanup = time.time() * 1000
        self.track_limit = 500
        self.__count_since_boot = 0

    def update(self, tracked_objects):
        now = int(time.time() * 1000)
        for obj in tracked_objects:
            if obj["id"] is not None and obj["label"] == "person":
                if obj["id"] in self.movements_by_trackid:
                    self.movements_by_trackid[obj["id"]][1] = now
                else:
                    self.__count_since_boot += 1
                    movements = [now, now, obj["id"]]
                    self.movements.append(movements)
                    self.movements_by_trackid[obj["id"]] = movements

    def get_count(self, from_seconds, to_seconds):
        from_ms = int(from_seconds * 1000)
        to_ms = int(to_seconds * 1000)
        count = 0
        total_time = 0
        for first_movement, latest_movement, _ in self.movements:
            if first_movement < to_ms and latest_movement > from_ms:
                overlap_start = max(first_movement, from_ms)
                overlap_end = min(latest_movement, to_ms)
                overlap_duration = overlap_end - overlap_start
                if overlap_duration > 300:  # 300 ms minimum duration
                    count += 1
                    total_time += overlap_duration

        self.cleanup()

        if total_time > 0:
            # Calculate the average count over the time period
            time_period = to_ms - from_ms
            return (count * time_period) / total_time
        return 0

    def cleanup(self):
        now = int(time.time() * 1000)
        if now - self.last_cleanup < 1000 or len(self.movements) < self.track_limit:
            return
        self.last_cleanup = now
        self.movements = sorted(self.movements, key=lambda x: x[1], reverse=True)[: self.track_limit]
        self.movements_by_trackid = {x[2]: x for x in self.movements}

    def get_count_since_boot(self):
        return self.__count_since_boot
