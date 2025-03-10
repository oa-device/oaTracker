import datetime
import os
from queue import Queue
import time
from typing import Any, TypedDict, Union
from uuid import uuid4
import uuid
import cv2
from shapely import Point, Polygon
import ultralytics.engine.results
import ultralytics.trackers.bot_sort

from app.counters import Counter
from app.utils.time_int import time_int


import pyarrow as pa
import pyarrow.parquet as pq


class ZoneCounterPoint(TypedDict):
    x: float
    y: float
    current_zone: int


class ZoneCounterZone(TypedDict):
    first_seen: float
    last_seen: float
    enter_event_id: bytes
    leave_event_id: bytes


class ZoneCounterTrack(dict):
    def __init__(
        self,
        id: int,
        x: float,
        y: float,
        current_zone: int,
        track_names: tuple[str, str, str],
        track_class: int,
        track_id: bytes,
        cam_id: bytes,
    ):
        self.id = id
        self.track_names = track_names

        self.conf = 0
        self.track_id = track_id
        self.cam_id = cam_id

        self.track_class = track_class
        self.point = ZoneCounterPoint(x=x, y=y, current_zone=current_zone)
        self.zones = [
            ZoneCounterZone(
                first_seen=0.0,
                last_seen=0.0,
                enter_event_id=uuid4().bytes,
                leave_event_id=uuid4().bytes,
            )
            for _ in range(len(track_names))
        ]
        self.live_row: Union[dict[str, Any], None] = None
        self.done_rows: list[dict[str, Any]] = []

    def update_present(
        self, now: float, x: float, y: float, current_zone: int, conf: int
    ):
        i = -1
        # print("update present", now, x, y, current_zone)
        last_zone = int(self.point["current_zone"])
        self.point.update({"x": x, "y": y, "current_zone": current_zone})

        self.conf = max(conf, self.conf)

        zone_changed = last_zone != current_zone

        if zone_changed and self.live_row:
            self.done_rows.append(self.live_row)

        for zone in self.zones:
            i += 1

            if current_zone == i:
                if zone["last_seen"] == 0.0:
                    # newly in frame
                    self.live_row = {
                        "event_ts": 0.0,
                        "event_id": zone["leave_event_id"],
                        "event_name": f"leave_zone_{self.track_names[i]}",
                        "track_conf": self.conf,
                        "track_class": self.track_class,
                        "track_id": self.track_id,
                        "cam_id": self.cam_id,
                    }
                    self.done_rows.append(
                        {
                            "event_ts": now * 1000000,
                            "event_id": zone["enter_event_id"],
                            "event_name": f"enter_zone_{self.track_names[i]}",
                            "track_conf": self.conf,
                            "track_class": self.track_class,
                            "track_id": self.track_id,
                            "cam_id": self.cam_id,
                        }
                    )

                if self.live_row is not None:
                    self.live_row["event_ts"] = now * 1000000

                zone["first_seen"] = (
                    zone["first_seen"] if zone["first_seen"] != 0.0 else now
                )
                zone["last_seen"] = now

            elif zone["last_seen"] != 0.0:
                zone["first_seen"] = 0.0
                zone["last_seen"] = 0.0
                zone["enter_event_id"] = uuid4().bytes
                zone["leave_event_id"] = uuid4().bytes

    def get_rows(self, last_update):
        _done_rows = self.done_rows.copy()
        self.done_rows = []
        # print('self.live_row', self.live_row)
        live_rows = []
        if self.live_row is not None and self.live_row["event_ts"] < last_update:
            _done_rows.append(self.live_row)
            self.live_row = None
        elif self.live_row is not None:
            live_rows.append(self.live_row)

        return {"live": live_rows, "done": _done_rows}


schema = pa.schema(
    [
        pa.field("event_ts", pa.timestamp("us"), nullable=False),
        pa.field("event_id", pa.binary(16), nullable=False),
        pa.field("event_name", pa.string(), nullable=False),
        pa.field("track_conf", pa.int8(), nullable=False),
        pa.field("track_class", pa.int8(), nullable=False),
        pa.field("track_id", pa.binary(16), nullable=False),
        pa.field("cam_id", pa.binary(16), nullable=False),
    ]
)


def write_files(q: Queue, boot_int: int):

    while True:
        from_queue = q.get()
        begin = time.monotonic()
        # print('from_queue', from_queue)
        live_row = from_queue[0]
        done_rows = from_queue[1]
        done_int = from_queue[2]

        # print("writes", (time.monotonic() - begin) * 1000, 'live', live_rows_arrow.num_rows, 'done', done_rows_arrow.num_rows, 'update_done', update_done)


class ZoneCounter(Counter):

    name = "zone_counter"

    def __init__(self, args) -> None:
        self.classes = [0, 2, 3, 5]
        super().__init__(args, ZoneCounter.name)

        self.setup()

        self.data: dict[int, ZoneCounterTrack] = dict({})

        self.data_by_trackid: dict[
            bytes,
            tuple[
                int,
                bytes,
                list[Union[tuple[float, float], int, float]],
                list[list[Union[bool, bytes, float]]],
            ],
        ] = dict({})
        self.deleted: list[int] = []
        self.last_db_update = 0.0
        self.rows_deleted_tracks_live = []
        self.rows_deleted_tracks_done = []
        self.done_int = self.args.boot_int
        self.done_rows_arrow = schema.empty_table()
        self.last_done_int = self.args.boot_int

        self.cam_id_bytes = uuid.UUID(args.camId).bytes
        self.cam_id_hex = str(uuid.UUID(args.camId).hex).upper()

        self.write_thread_queue: Queue[dict[str, Any]] = Queue()

        # , list[list[Union[int, float, bytes]]]

    def update(
        self,
        now: float,
        boxes: ultralytics.engine.results.Boxes,
        removed_stracks: list[Any],
    ) -> None:
        try:
            self.last_update = now

            print(boxes)

            # start with tracks that were in the frame
            box_ids = []
            for box in boxes:
                if box.id is None:
                    continue
                id = int(box.id)
                box_ids.append(id)
                center_x = float(box.xywh[0][0])
                bottom_y = float(box.xyxy[0][3])
                small_quarter_wh = min(float(box.xywh[0][2]), float(box.xywh[0][3])) / 6
                x = center_x
                y = float(bottom_y - small_quarter_wh)

                uuid = self.track_uuids[id]
                new_track = id not in self.data
                conf = int(box.conf * 100)
                track_class = int(box.cls)

                current_zone = -1
                i = -1
                for zone_shape in self.zones_shape:
                    i += 1
                    contains = zone_shape.contains(Point(x, y))  # type: ignore
                    if contains:
                        current_zone = i

                if new_track:
                    self.data[id] = ZoneCounterTrack(
                        id,
                        x,
                        y,
                        current_zone,
                        self.zones_name,
                        track_class,
                        cam_id=self.cam_id_bytes,
                        track_id=uuid,
                    )

                self.data[id].update_present(now, x, y, current_zone, conf)

            # update tracks not in frame
            # tracks_not_in_frame = [
            #     track for id, track in self.data.items() if not id in box_ids
            # ]
            # for track_not_in_frame in tracks_not_in_frame:
            #     print("not in frame", track_not_in_frame.id)

            # cleanup
            # to_write = []
            # for not_deleted in [
            #     x.track_id
            #     for x in removed_stracks
            #     if x.track_id not in self.deleted
            # ]:
            #     if not_deleted in self.data:
            #         rows = self.data[not_deleted].get_rows()
            #         self.rows_deleted_tracks_live.append(rows["live"])
            #         self.rows_deleted_tracks_done += rows["done"]
            #         del self.data[not_deleted]

            # self.deleted = self.deleted + sorted(
            #     set([x.track_id for x in removed_stracks]) - set(self.deleted)
            # )

            if now - self.last_db_update > 1:
                self.update_db()
                self.last_db_update = now
        except Exception as e:
            print(e)

    def update_db(self):
        begin = time.time()
        rows_deleted_tracks_live = self.rows_deleted_tracks_live
        rows_deleted_tracks_done = self.rows_deleted_tracks_done
        self.rows_deleted_tracks_live = []
        self.rows_deleted_tracks_done = []

        last_db_update_ms = self.last_db_update * 1000000

        rows = [data.get_rows(last_db_update_ms) for data in self.data.values()]
        done_rows = [
            row for _rows in rows for row in _rows["done"]
        ] + rows_deleted_tracks_done
        live_rows = [
            row for _rows in rows for row in _rows["live"]
        ] + rows_deleted_tracks_live

        live_rows = [row for row in live_rows if row["event_ts"] > last_db_update_ms]

        schema = pa.schema(
            [
                pa.field("event_ts", pa.timestamp("us"), nullable=False),
                pa.field("event_id", pa.binary(16), nullable=False),
                pa.field("event_name", pa.string(), nullable=False),
                pa.field("track_conf", pa.int8(), nullable=False),
                pa.field("track_class", pa.int8(), nullable=False),
                pa.field("track_id", pa.binary(16), nullable=False),
                pa.field("cam_id", pa.binary(16), nullable=False),
            ]
        )

        update_live = len(live_rows) != 0
        update_done = len(done_rows) != 0

        if update_live:
            live_rows_arrow = pa.Table.from_pylist(live_rows, schema=schema)
            pq.write_table(
                live_rows_arrow, "/tmp/live.parquet.tmp", compression="snappy"
            )

        hive_path = f"year={datetime.datetime.now(datetime.timezone.utc).year}/month={datetime.datetime.now(datetime.timezone.utc).month}/cam_id_hex={self.cam_id_hex}"

        from pathlib import Path

        Path(f"/tmp/warehouse_oa/{hive_path}").mkdir(parents=True, exist_ok=True)
        if update_done:
            self.done_rows_arrow = pa.concat_tables(
                [pa.Table.from_pylist(done_rows, schema=schema), self.done_rows_arrow]
            )
            pq.write_table(
                self.done_rows_arrow, "/tmp/done.parquet.tmp", compression="snappy"
            )
            os.replace(
                "/tmp/done.parquet.tmp",
                f"/tmp/warehouse_oa/{hive_path}/done-{self.args.boot_int}-{self.done_int}.parquet",
            )
            split = len(self.done_rows_arrow) > 10_000
            if split:
                self.done_int = time_int()
                self.done_rows_arrow = schema.empty_table()

        if update_live:
            os.replace(
                "/tmp/live.parquet.tmp",
                f"/tmp/warehouse_oa/{hive_path}/live-{self.args.boot_int}.parquet",
            )

        # print('update', (time.time() - begin)*1000, 'LIVE', live_count, 'done', done_count)

    def setup(self):
        zones_coords = []
        self.zone_count = len(self.counter_config["zones"])
        for zone in self.counter_config["zones"]:
            coords = []
            for points in zone["points"]:
                coords.append((int(points[0] * 12.8), int(points[1] * 7.2)))
            zones_coords.append(coords)
        self.zones_coords = tuple(zones_coords)

        zones_shape = []
        for coords in self.zones_coords:
            zones_shape.append(Polygon(coords))
        self.zones_shape: tuple[Polygon] = tuple(zones_shape)  # type: ignore

        background_small_zones_lines = []
        for zone_shape in self.zones_shape:
            background_small_zone_lines = []
            coords = zone_shape.buffer(-2).exterior.coords
            coords_count = len(coords)
            for i in range(0, coords_count - 1):
                line = (
                    (int(coords[i][0]), int(coords[i][1])),
                    (int(coords[i + 1][0]), int(coords[i + 1][1])),
                )
                background_small_zone_lines.append(line)
            background_small_zones_lines.append(tuple(background_small_zone_lines))

        self.background_small_zones_lines = tuple(background_small_zones_lines)

        zones_color = []
        for zone in self.counter_config["zones"]:
            zones_color.append(tuple(reversed(zone["color"])))
        self.zones_color = tuple(zones_color)

        zones_name = []
        for zone in self.counter_config["zones"]:
            zones_name.append(zone["name"])
        self.zones_name = tuple(zones_name)

        self.zones_count = len(zones_name)

    def get_label(self, id: int) -> str | None:
        return str(uuid.UUID(bytes=self.track_uuids[id], version=4))[:8]

    def plot(self, img: bytearray, boxes):
        # background
        i = 0
        for background_small_zone_lines in self.background_small_zones_lines:
            background_small_zone_lines = self.background_small_zones_lines[i]
            for line in background_small_zone_lines:
                img = cv2.line(
                    img,  # type: ignore
                    line[0],
                    line[1],
                    self.zones_color[i],
                    thickness=2,
                    lineType=cv2.LINE_AA,
                )
            i += 1

        # tracking points
        ids = [int(b.id) for b in boxes if b.id is not None]

        for id in self.data:
            if id not in ids:
                continue
            point = self.data[id].point
            img = cv2.circle(
                img,  # type: ignore
                center=(int(point["x"]), int(point["y"])),
                color=(255, 255, 255) if point["current_zone"] == -1 else self.zones_color[point["current_zone"]],  # type: ignore
                radius=6,
                thickness=-1,
            )

        return img
