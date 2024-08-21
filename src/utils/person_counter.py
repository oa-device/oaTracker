import time

class PersonCounter:
    def __init__(self, device_index):
        self.device_index = device_index
        self.movements_by_trackid = {}
        self.movements = []
        self.last_cleanup = time.time()
        self.track_limit = 500
        self.__count_since_boot = 0

    def update(self, tracked_objects):
        now = time.time() * 1000
        for obj in tracked_objects:
            if obj['id'] is not None:
                if obj['id'] in self.movements_by_trackid:
                    self.movements_by_trackid[obj['id']][1] = now
                else:
                    self.__count_since_boot += 1
                    movements = [now, now, obj['id']]
                    self.movements.append(movements)
                    self.movements_by_trackid[obj['id']] = movements

    def get_count(self, _from, to):
        count = 0
        for x in self.movements:
            first_movement, latest_movement, _ = x
            if (first_movement < to and latest_movement > _from and
                latest_movement - first_movement > 300):
                count += 1
        self.cleanup()
        return count

    def cleanup(self):
        if time.time() - self.last_cleanup < 1 or len(self.movements) < self.track_limit:
            return
        self.last_cleanup = time.time()
        self.movements = sorted(self.movements, key=lambda x: x[1], reverse=True)[:self.track_limit]
        self.movements_by_trackid = dict(zip([x[2] for x in self.movements], self.movements))

    def get_count_since_boot(self):
        return self.__count_since_boot