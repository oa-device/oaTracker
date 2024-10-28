import os
import time
from typing import Any, Union
import uuid

from app.counters import Counter
import ultralytics.engine.results
import ultralytics.trackers.bot_sort

from app.parse_args import Args
from app.utils.logger import create_log_message, get_logger


logger = get_logger(__name__)


cam_id_bytes = uuid.UUID(os.environ["CAM_ID"]).bytes


class GenericCounter(Counter):

    def __init__(self, args: Args, name: str, cls: int):
        super().__init__(args, name)
        self.cls = cls
        self.classes = [cls]
        self.data_by_trackid: dict[bytes, tuple[float, bytes, float, float]] = dict({})
        self.deleted: list[int] = []
        self.last_db_update = 0.0

    def update(self, boxes: ultralytics.engine.results.Boxes, tracker: ultralytics.trackers.bot_sort.BOTSORT) -> None:
        now = time.time()

        for t in boxes:
            try:
                if (
                    t.is_track
                    and int(t.cls) == self.cls
                ):
                    uuid = self.track_uuids[int(t.id)]  # type: ignore
                    if uuid in self.data_by_trackid:  # track is known
                        first_seen,  track_id, max_conf, _1  = self.data_by_trackid[uuid]
                        self.data_by_trackid[uuid] = (
                            first_seen, track_id, max(max_conf, float(t.conf)), now
                        )
                    else:  # track is unknown, add it
                        self.data_by_trackid[uuid] = (
                            now,
                            uuid,
                            float(t.conf),
                            now
                        )

            except Exception as e:
                print("this weird box", t, e)

        # cleanup
        for not_deleted in [x.track_id for x in tracker.removed_stracks if x.track_id not in self.deleted]:
            print(not_deleted, self.track_uuids)
            if not_deleted in self.track_uuids:
                not_deleted_uuid = self.track_uuids[not_deleted]
                if not_deleted_uuid in self.data_by_trackid:
                    del self.data_by_trackid[not_deleted_uuid]
            
        self.deleted = self.deleted + sorted(set([x.track_id for x in tracker.removed_stracks]) - set(self.deleted))
    
        if now - self.last_db_update > 1.0:
            self.update_db(now)


    def collect(self):
        #return [self.data_by_trackid[x][:-1] for x in self.data_by_trackid], self.meta  
        return [[],{}]

    def update_db(self, now:float):
        first=[]
        last=[]
        for id in self.data_by_trackid:
            first_seen, track_id, conf, last_seen = self.data_by_trackid[id]
            last.append(
                (
                    uuid.uuid4().bytes,
                    last_seen,
                    "person_last_seen",
                    cam_id_bytes,
                    track_id,
                    conf
                )
            )
            first.append(
                (
                    uuid.uuid4().bytes,
                    first_seen,
                    "person_first_seen",
                    cam_id_bytes,
                    track_id,
                    conf
                )
            )
            
        cursor = self.connection.cursor()
        cursor.executemany(
            "INSERT INTO events(event_id, ts, name, cam_id, track_id, conf) values (?, ?, ?, ?, ?, ?) ON CONFLICT(name, track_id) DO UPDATE SET conf=excluded.conf",
            first,
        )
                    
        cursor.executemany(
            "INSERT INTO events(event_id, ts, name, cam_id, track_id, conf) values (?, ?, ?, ?, ?, ?) ON CONFLICT(name, track_id) DO UPDATE SET ts=excluded.ts, conf=excluded.conf",
            last,
        )
        
        self.connection.commit()
        cursor.close()
        self.last_db_update = now

