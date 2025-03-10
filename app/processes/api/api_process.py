import asyncio
from contextlib import asynccontextmanager
import gzip
import json
import os
import signal
import time
from typing import Callable
import uuid
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import functools
import psutil
from sse_starlette import EventSourceResponse
import uvicorn
from app.parse_args import Args
from app.processes.api.frame_streamer import FrameStreamer


from fastapi.middleware.cors import CORSMiddleware

from app.utils.stop_detection import stop_detection
from app.utils.logger import get_logger

import duckdb
import pyarrow as pa
from duckdb.typing import *


duckdb_con = duckdb.connect()

# Allow these origins to access the API
origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:8080",
    "https://jpr1.net",
]

# Allow these methods to be used
methods = ["GET", "POST", "PUT", "DELETE"]

# Only these headers are allowed
headers = ["Content-Type", "Authorization"]

# camera feed jpg is a streaming response route lazily loading the last image we have from the detector
fs: FrameStreamer  # type: ignore
fs = FrameStreamer()


@functools.lru_cache(maxsize=128)
def numberToBase(n, b):
    if n == 0:
        return [0]
    digits = []
    while n:
        digits.append(int(n % b))
        n //= b
    return digits[::-1]


urlsafe_66_alphabet = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-.~"
)


@functools.lru_cache(maxsize=128)
def bytes_to_uuid(b: bytes):
    return str(uuid.UUID(bytes=b, version=4))[:8]


running = True


app = FastAPI()


class TimedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            before = time.time()
            response: Response = await original_route_handler(request)
            duration = time.time() - before
            response.headers["X-Response-Time"] = str(duration)
            print(f"route duration: {duration}")
            print(f"route response: {response}")
            print(f"route response headers: {response.headers}")
            return response

        return custom_route_handler


router = APIRouter(route_class=TimedRoute)
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=methods,
    allow_headers=headers,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

logger = get_logger(__name__)


# used to show in the dashboard when the app is offline and to reboot when it's back online
@app.get("/online")
def online():
    global server_stopped
    return not server_stopped.is_set()


import yaml


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html.jinja", {"request": request, "dashboard_data": {}})  # type: ignore


@app.get("/edit_config", response_class=HTMLResponse)
async def config_editor(request: Request):
    return templates.TemplateResponse("config/index.html.jinja", {"request": request, "config_data": args})  # type: ignore


@app.get("/config", response_class=HTMLResponse)
async def get_config(request: Request):
    with open("./config.yaml", "r") as file:
        config = yaml.safe_load(file)
        return json.dumps(config)


@app.post("/config", response_class=HTMLResponse)
async def post_config(request: Request):
    with open("./config.yaml", "w") as file:
        data = await request.json()
        
        print(data)
        
        yaml.dump(data, file)
        
        stop_detection("reload_config", {}, True)
        return json.dumps({"ok": True})
    print(request)


client_last_presence = 0


@app.get("/dashboard/sse")
async def message_stream(start: str = "entrance", end: str = "exit"):
    async def event_generator():
        global client_last_presence, server_stopped
        while not server_stopped.is_set():
            try:
                client_last_presence = time.time()
                cur = duckdb_con.cursor()
                yield {
                    "id": str(client_last_presence),
                    "retry": 15000,
                    "data": json.dumps(
                        [
                            [],  # api_zone_movement(cur, start, end),
                            [],  # api_zone_last_15(cur),
                            api_last_seen_from(cur),
                            api_first_seen_from(cur),
                            api_mean_dwell(cur),
                            api_total_presence(cur),
                            api_presence_last_15_seconds(cur),
                        ]
                    ),
                }
                cur.close()
            except Exception as e:
                print(e)
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


def api_zone_movement(cur, start="entrance", end="exit"):
    try:
        return []
        result = cur.sql(
            f"""SELECT 
        track_id,
        MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) as start_ts,
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) as end_ts,
        strftime(start_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as start,
        strftime(end_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as end
    FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT})
    GROUP BY track_id
    HAVING MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) IS NOT NULL
    AND MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) IS NOT NULL
    AND MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) < 
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) ORDER BY start_ts DESC LIMIT 15;"""
        ).fetchall()

    except:
        return []
    return [(bytes_to_uuid(x[0]), str(x[3]), str(x[4])) for x in result]


def api_zone_last_15(cur):
    return []
    try:
        result = cur.sql(
            """SELECT track_id, event_ts as _event_ts, strftime(event_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as event_ts, event_name, track_conf, track_class FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT}) ORDER BY _event_ts DESC LIMIT 15;"""
        ).fetchall()
    except:
        return []
    return [
        (bytes_to_uuid(x[0]), str(x[1]), str(x[2]), str(x[3]), str(x[4]))
        for x in result
    ]


def api_last_seen_from(cur):
    try:
        result = cur.sql(
            """WITH last_events AS (
            SELECT t.track_id, t.event_name
            FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT}) t
            INNER JOIN (
                SELECT track_id, MAX(event_ts) as max_ts
                FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT})
                GROUP BY track_id
            ) m ON t.track_id = m.track_id AND t.event_ts = m.max_ts
        )
        SELECT 
            COUNT(CASE WHEN event_name LIKE 'leave_zone_out_top_left' THEN 1 END) as last_seen_zone_out_top_left,
            COUNT(CASE WHEN event_name LIKE 'leave_zone_out_door_right' THEN 1 END) as last_seen_zone_out_door_right,
            COUNT(CASE WHEN event_name LIKE 'leave_zone_out_door_left' THEN 1 END) as last_seen_zone_out_door_left,
            COUNT(CASE WHEN event_name LIKE 'leave_zone_out_bottom_right' THEN 1 END) as last_seen_zone_out_bottom_right,
            COUNT(CASE WHEN event_name LIKE 'leave_zone_out_bottom' THEN 1 END) as last_seen_zone_out_bottom
        FROM last_events;"""
        ).fetchall()[0]

    except:
        return []
    return {
        "last_seen_zone_out_top_left": result[0],
        "last_seen_zone_out_door_right": result[1],
        "last_seen_zone_out_door_left": result[2],
        "last_seen_zone_out_bottom_right": result[3],
        "last_seen_zone_out_bottom": result[4],
    }


def api_first_seen_from(cur):
    try:
        result = cur.sql(
            """
            WITH first_events AS (
                SELECT t.track_id, t.event_name
                FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT}) t
                INNER JOIN (
                    SELECT track_id, MIN(event_ts) as max_ts
                    FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT})
                    GROUP BY track_id
                ) m ON t.track_id = m.track_id AND t.event_ts = m.max_ts
            )
            SELECT 
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_top_left' THEN 1 END) as first_seen_zone_out_top_left,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_door_right' THEN 1 END) as first_seen_zone_out_door_right,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_door_left' THEN 1 END) as first_seen_zone_out_door_left,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_bottom_right' THEN 1 END) as first_seen_zone_out_bottom_right,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_bottom' THEN 1 END) as first_seen_zone_out_bottom FROM first_events;"""
        ).fetchall()[0]

    except:
        return []
    return {
        "first_seen_zone_out_top_left": result[0],
        "first_seen_zone_out_door_right": result[1],
        "first_seen_zone_out_door_left": result[2],
        "first_seen_zone_out_bottom_right": result[3],
        "first_seen_zone_out_bottom": result[4],
    }


def api_mean_dwell(cur):
    try:
        result = cur.sql(
            """
            WITH DwellTimes AS (
    SELECT
        track_id,
        MIN(event_ts) AS start_time,
        MAX(event_ts) AS end_time,
        (EPOCH(MAX(event_ts)) - EPOCH(MIN(event_ts))) AS dwell_time_seconds
    FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT})
    GROUP BY track_id
)
SELECT
    AVG(dwell_time_seconds) AS mean_dwell_time_seconds
FROM DwellTimes;"""
        ).fetchall()[0]

    except:
        return []
    return result[0]


def api_total_presence(cur):
    try:
        result = cur.sql(
            """
            WITH DwellTimes AS (
        SELECT
            track_id,
            EPOCH(MAX(event_ts)) - EPOCH(MIN(event_ts)) AS dwell_time_seconds
        FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT})
        GROUP BY track_id
    )
    SELECT
        COUNT(DISTINCT track_id) AS total_track_count,
        SUM(dwell_time_seconds) AS total_time_spent_seconds
    FROM DwellTimes;"""
        ).fetchall()[0]

    except Exception as e:
        print(e)
        return []
    return result


def api_presence_last_15_seconds(cur):
    try:
        result = cur.sql(
            """SELECT
            COUNT(DISTINCT track_id)
            FROM read_parquet('/tmp/warehouse_oa/*/*/*/*.parquet' , hive_partitioning = true, hive_types = {'year': SMALLINT, 'month': TINYINT}) WHERE event_ts AT TIME ZONE 'UTC' > current_timestamp - INTERVAL '15 seconds';"""
        ).fetchall()[0]

    except Exception as e:
        print(e)
        return []
    return result


@app.get("/cam.jpg")
def video_feed():
    return fs.get_stream()  # type: ignore


from multiprocessing.synchronize import Event as EventClass

args: Args = None  # type:ignore
server_stopped: EventClass = None # type:ignore
class ApiProcess:
    def __init__(self, _args: Args, _server_stopped: EventClass):
        global args, server_stopped

        args = _args
        server_stopped = _server_stopped
        
    async def close(self):
        self.server.should_exit = True
        self.server.force_exit = True
        # await self.server.shutdown()

    def start(self):
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info", loop="asyncio")
        self.server = uvicorn.Server(config=config)
        self.server.run()
