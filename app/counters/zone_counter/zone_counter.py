import json
import threading
import time
import traceback
from typing import Any
from uuid import uuid4
import uuid
import cv2
from shapely import Point, Polygon
import torch
import ultralytics.engine.results
import pyarrow.flight as flight
from app.counters import Counter
from shapely.prepared import prep
from queue import Queue

import pyarrow as pa
import pyarrow.parquet as pq


def connect_with_retry(remote=False, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            client = flight.connect(f"grpc://{'localhost' if not remote else 'detectiondb.orangead.ca' }:8815")
            return client
        except flight.FlightUnavailableError:
            if attempt < max_attempts - 1:
                print(
                    f"Connection attempt {attempt + 1} failed, retrying in 1 second..."
                )
                time.sleep(1)
            else:
                raise


def db_thread(q, remote=False):
    client = connect_with_retry(remote)
    while True:
        try:
            try:
                item = q.get(timeout=0.01)
            except:
                continue
            if item is None:
                continue
            client.wait_for_available(timeout=10)
            print(item[1])
            writer, _ = client.do_put(item[0], item[1].schema)
            writer.write_table(item[1])
            writer.close()
        except Exception as e:
            tbe = traceback.TracebackException.from_exception(e)
            stack_frames = traceback.extract_stack()
            tbe.stack.extend(stack_frames)
            formatted_traceback = "".join(tbe.format())
            print(f"Formatted Traceback:\n{formatted_traceback}")
            print(e)
            client = connect_with_retry(remote)
            time.sleep(0.01)
            pass

class ZoneCounter(Counter):

    name = "zone_counter"

    def __init__(self, args) -> None:
        self.classes = [0, 2, 3, 5]
        super().__init__(args, ZoneCounter.name)
        self.setup()

        self.data: dict[int, list[list]] = dict({})
        self.pos: dict[int, list[int]] = dict({})

        self.last_db_update = 0.0
        self.boot_int = self.args.boot_int

        self.cam_id = args.camId

        self.THREE_HOURS = 60 * 60 * 3
        self.device = None
        
        self.local_queue = Queue(maxsize=0)
        self.remote_queue = Queue(maxsize=0)
        
        self.local_thread = threading.Thread(target=db_thread, args=(self.local_queue,False))
        self.remote_thread = threading.Thread(target=db_thread, args=(self.remote_queue,True))
        self.local_thread.start()
        self.remote_thread.start()
    

    def update(
        self,
        now: float,
        boxes: ultralytics.engine.results.Boxes,
        _removed_stracks: list[Any],
    ) -> None:
        try:
            valid_indices = [i for i, box in enumerate(boxes) if box.id is not None]

            if not valid_indices:
                if now - self.last_db_update > 1:
                    self.update_db(
                        now, set(int(strack_id.idx) for strack_id in _removed_stracks)
                    )
                    self.last_db_update = now
                return

            valid_boxes = [boxes[i] for i in valid_indices]

            if self.device is None:
                dev = boxes[0].xywh.get_device()
                self.device = "cpu" if dev < 0 else dev

            ids = [int(box.id.item()) for box in valid_boxes]

            xywh_data = torch.stack([box.xywh[0] for box in valid_boxes]).to(
                self.device
            )
            xyxy_data = torch.stack([box.xyxy[0] for box in valid_boxes]).to(
                self.device
            )

            center_x = xywh_data[:, 0]
            bottom_y = xyxy_data[:, 3]

            widths = xywh_data[:, 2]
            heights = xywh_data[:, 3]
            small_quarter_wh = torch.minimum(widths, heights) / 6

            x_points = center_x
            y_points = bottom_y - small_quarter_wh

            conf_values = torch.stack([box.conf for box in valid_boxes]) * 100
            conf_values = conf_values.to(torch.int32)
            track_classes = torch.stack([box.cls for box in valid_boxes]).to(
                torch.int32
            )

            for i, id_val in enumerate(ids):
                track_uuid = self.track_uuids[id_val]
                known_track = id_val in self.data
                conf = conf_values[i].item()
                track_class = track_classes[i].item()

                x, y = x_points[i].item(), y_points[i].item()
                current_zone = -1
                point = Point(x, y)
                for zone_idx, prepared_zone in enumerate(self.prepared_zones):
                    if prepared_zone.contains(point):
                        current_zone = zone_idx
                        break

                if id_val not in self.pos:
                    self.pos[id_val] = [x, y, current_zone]
                else:
                    self.pos[id_val][0] = x
                    self.pos[id_val][1] = y
                    if self.pos[id_val][2] != current_zone:
                        self.pos[id_val][2] = current_zone

                zone_name = self.zones_name[current_zone]

                if not known_track:
                    self.data[id_val] = []

                if (
                    known_track
                    and len(self.data[id_val]) != 0
                    and self.data[id_val][0][2] == f"zone_leave_{zone_name}"
                ):
                    self.data[id_val][0][0] = now * 1000000
                    if self.data[id_val][0][3] < conf:
                        self.data[id_val][0][3] = conf
                    self.data[id_val][0][6] = False
                else:
                    track_uuid_obj = uuid.UUID(bytes=track_uuid, version=4)
                    self.data[id_val].insert(
                        0,
                        [
                            now * 1000000,
                            uuid4(),
                            f"zone_enter_{zone_name}",
                            conf,
                            track_class,
                            track_uuid_obj,
                            False,
                        ],
                    )

                    self.data[id_val].insert(
                        0,
                        [
                            now * 1000000 + 5000,  # add 5ms
                            uuid4(),
                            f"zone_leave_{zone_name}",
                            conf,
                            track_class,
                            track_uuid_obj,
                            False,
                        ],
                    )

            if now - self.last_db_update > 1:
                self.update_db(
                    now, set(int(strack_id.idx) for strack_id in _removed_stracks)
                )
                self.last_db_update = now
        except Exception as e:
            tbe = traceback.TracebackException.from_exception(e)
            stack_frames = traceback.extract_stack()
            tbe.stack.extend(stack_frames)
            formatted_traceback = "".join(tbe.format())
            print(f"Formatted Traceback:\n{formatted_traceback}")
            print(e)

    def update_db(self, now: float, removed_stracks: set[int]):
        to_delete_old = [
            id for id in self.data if self.data[id][0][0] + (1000000.0 * 60) < now * 1000000
        ]
        to_delete_untracked = [id for id in removed_stracks if id in self.data]
        to_delete = set(to_delete_old + to_delete_untracked)

        # cleanup before saving
        for id in to_delete:
            del self.data[id]

        updated_rows = [row for id in self.data for row in self.data[id] if not row[6]]

        if len(updated_rows) == 0:
            return

        schema = pa.schema(
            [
                pa.field("event_ts", pa.timestamp("us"), nullable=False),
                pa.field("event_id", pa.uuid(), nullable=False),
                pa.field("event_name", pa.string(), nullable=False),
                pa.field("track_conf", pa.int8(), nullable=False),
                pa.field("track_class", pa.int8(), nullable=False),
                pa.field("track_id", pa.uuid(), nullable=False),
                pa.field("cam_id", pa.uuid(), nullable=False),
            ]
        )

        pylist = [
            {
                "event_ts": row[0],
                "event_id": row[1].bytes,
                "event_name": row[2],
                "track_conf": row[3],
                "track_class": row[4],
                "track_id": row[5].bytes,
                "cam_id": uuid.UUID(self.cam_id).bytes,
            }
            for row in updated_rows
        ]

        metadata = json.dumps(
            {
                "table": "zone_events",
                "since": self.boot_int,
                "batch_id": str(uuid.uuid4()),
            }
        ).encode("utf-8")

        descriptor = flight.FlightDescriptor.for_path(metadata)

        table = pa.Table.from_pylist(pylist, schema)

        # Upload the data
        
        self.do_put((descriptor, table))
        
        # cleanup post save
        for id in self.data:
            self.data[id][0][6] = True
            self.data[id] = [self.data[id][0]]

    def do_put(self, data):
        self.local_queue.put(data)
        self.remote_queue.put(data)

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

        self.prepared_zones = [prep(zone) for zone in zones_shape]

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
            [x, y, zone] = self.pos[id]
            img = cv2.circle(
                img,  # type: ignore
                center=(int(x), int(y)),
                color=(255, 255, 255) if zone == -1 else self.zones_color[zone],  # type: ignore
                radius=6,
                thickness=-1,
            )

        return img
