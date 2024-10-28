

import os
import time
from typing import Union
from uuid import uuid4
import uuid
import cv2
from shapely import Point, Polygon
import ultralytics.engine.results
import ultralytics.trackers.bot_sort

from app.counters import Counter

cam_id_bytes = uuid.UUID(os.environ["CAM_ID"]).bytes

class ZoneCounter(Counter):
    name = "zone_counter"
    def __init__(self, args) -> None:
        self.classes = [0]
        super().__init__(args, ZoneCounter.name)
        
        self.setup()
        self.data_by_trackid: dict[bytes, tuple[int, bytes, list[Union[tuple[float, float], int, float]], list[list[Union[bool, bytes, float]]]]] = dict({})
        self.deleted: list[int] = []
        self.last_db_update = 0.0
        # , list[list[Union[int, float, bytes]]]
    
    def update(self, boxes: ultralytics.engine.results.Boxes, tracker: ultralytics.trackers.bot_sort.BOTSORT) -> None:
        now = time.time()
        
        #add new tracks
        for box in boxes:
            id = int(box.id)
            center_x = float(box.xywh[0][0])
            bottom_y = float(box.xyxy[0][3])
            small_quarter_wh = min(
                float(box.xywh[0][2]),
                float(box.xywh[0][3])
            ) / 6
            
            uuid = self.track_uuids[id]
            new_track = uuid not in self.data_by_trackid
            conf = float(box.conf)
            
            point: list[Union[tuple[float, float], int]] =  [(0.0,0.0), -1] if new_track else self.data_by_trackid[uuid][2]
            zones:list[list[bool | bytes]] = [[False, uuid4().bytes, 0.0, 0.0, -1.0] for i in range(0,self.zone_count)] if new_track else self.data_by_trackid[uuid][3]
            
            if new_track:
                self.data_by_trackid[uuid] = (id, uuid4().bytes, point, zones)
            
            point[0] = (float(center_x), float(bottom_y - small_quarter_wh))
            point[1] =  -1
            
            
            i=-1
            for zone_shape in self.zones_shape:
                i+=1
                contains = zone_shape.contains(Point(point[0][0], point[0][1])) # type: ignore
                if contains:
                    point[1] = i
                    zones[i][0] = True
                    if zones[i][4] < 0.0: # set begin if first frame
                        zones[i][2] = now
                    zones[i][3] = now
                    zones[i][4] = max(zones[i][4], conf)
                elif zones[i][4] > 0.0: # reset
                    zones[i][0] = False
                    zones[i][1] = uuid4().bytes
                    zones[i][2] = 0.0
                    zones[i][3] = 0.0
                    zones[i][4] = -1.0
                    
                
            
        # cleanup
        for not_deleted in [x.track_id for x in tracker.removed_stracks if x.track_id not in self.deleted]:
            if not_deleted in self.track_uuids:
                not_deleted_uuid = self.track_uuids[not_deleted]
                if not_deleted_uuid in self.data_by_trackid:
                    del self.data_by_trackid[not_deleted_uuid]
            
        self.deleted = self.deleted + sorted(set([x.track_id for x in tracker.removed_stracks]) - set(self.deleted))
    
        if now - self.last_db_update > 1.0:
            self.update_db(now)
            
    def update_db(self, now:float):
        rows=[]
        for id in self.data_by_trackid:
            id, track_id, _, zones = self.data_by_trackid[id]
            i=-1
            for zone in zones:
                i+=1
                _, event_id, start, end, conf =  zone
                
                if conf < 0.0 or end < self.last_db_update: # type: ignore
                    continue
                
                rows.append(
                    (
                        event_id,
                        start,
                        end,
                        f"person_zone_{self.zones_name[i]}", # type: ignore
                        cam_id_bytes,
                        track_id,
                        conf,
                        0
                    )
                )
            
        cursor = self.connection.cursor()
        cursor.executemany(
            "INSERT INTO events(event_id, start, end, name, cam_id, track_id, conf, class) values (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(event_id) DO UPDATE SET conf=excluded.conf, end=excluded.end",
            rows,
        )
                    
        self.connection.commit()
        cursor.close()
        self.last_db_update = now
        
        
    def setup(self):
        zones_coords=[]
        self.zone_count = len(self.counter_config["zones"])
        for zone in self.counter_config["zones"]:
            coords=[]
            for points in zone["points"]:
                coords.append(
                    (int(points[0] * 6.4), int(points[1] * 4.8)))
            zones_coords.append(coords)
        self.zones_coords = tuple(zones_coords)
        
        zones_shape = []
        for coords in self.zones_coords:
            zones_shape.append(Polygon(coords))
        self.zones_shape: tuple[Polygon] = tuple(zones_shape) # type: ignore
        
        background_small_zones_lines = []
        for zone_shape in self.zones_shape:
            background_small_zone_lines = []
            coords=zone_shape.buffer(-2).exterior.coords
            coords_count=len(coords)
            for i in range(0, coords_count-1):
                    line = ((int(coords[i][0]), int(coords[i][1])), (int(coords[i+1][0]), int(coords[i+1][1])))
                    background_small_zone_lines.append(line)
            background_small_zones_lines.append(tuple(background_small_zone_lines))
        
        self.background_small_zones_lines = tuple(background_small_zones_lines)

        zones_color=[]
        for zone in self.counter_config["zones"]:
            zones_color.append(tuple(reversed(zone["color"])))
        self.zones_color=tuple(zones_color)
        
        zones_name=[]
        for zone in self.counter_config["zones"]:
            zones_name.append(zone["name"])
        self.zones_name=tuple(zones_name)


    def get_label(self, id: int) -> str | None:
        return ""

    def plot(self, img: bytearray):
        # background
        i = 0
        for background_small_zone_lines in self.background_small_zones_lines:
            background_small_zone_lines=self.background_small_zones_lines[i]
            for line in background_small_zone_lines:
                img = cv2.line(
                    img, # type: ignore
                    line[0],
                    line[1],
                    self.zones_color[i],
                    thickness=2,
                    lineType=cv2.LINE_AA,
                )
            i += 1
            
        # tracking points
        
        for trackid in self.data_by_trackid:
            (_1, _2, point, _3) = self.data_by_trackid[trackid]
            img = cv2.circle(
                img, # type: ignore
                center=(int(point[0][0]), int(point[0][1])),
                color=(255,255,255) if point[1] == -1 else self.zones_color[point[1]], # type: ignore
                radius=6,
                thickness=-1,
            )

        return img