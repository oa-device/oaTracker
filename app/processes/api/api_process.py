import asyncio
from contextlib import asynccontextmanager
import gzip
import json
import os
import signal
import time
from typing import Callable
import uuid
from fastapi import APIRouter, FastAPI,  Request,  Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import functools
from sse_starlette import EventSourceResponse
import uvicorn
from app.parse_args import Args
from app.processes.api.frame_streamer import FrameStreamer

from fastapi.middleware.cors import CORSMiddleware

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
    "https://jpr1.net"
]

# Allow these methods to be used
methods = ["GET", "POST", "PUT", "DELETE"]

# Only these headers are allowed
headers = ["Content-Type", "Authorization"]

# camera feed jpg is a streaming response route lazily loading the last image we have from the detector
fs: FrameStreamer # type: ignore 
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

urlsafe_66_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-.~'
@functools.lru_cache(maxsize=128)
def bytes_to_uuid(b:bytes):
    return str(uuid.UUID(bytes=b, version=4))[:8]

running = True

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # asyncio.create_task(handle_counter_events())
    def stop_server(*args):
        global running
        running = False
        fs.running = running
        os.kill(os.getpid(), signal.SIGTERM)
    signal.signal(signal.SIGINT, stop_server)
    yield

app = FastAPI(lifespan=lifespan)

class TimedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            print(111)
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
    global running
    return running


# the only route returning html
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html.jinja", {"request": request, "dashboard_data": {}})  # type: ignore

client_last_presence = 0 
@app.get("/dashboard/sse")
async def message_stream(start: str = 'entrance', end: str = "exit"):
    async def event_generator():
        global client_last_presence, running
        while running:
            try:
                client_last_presence = time.time()
                cur = duckdb_con.cursor()
                yield {
                    "id": str(client_last_presence),
                    "retry": 15000,
                    "data": json.dumps([api_zone_movement(cur, start, end), api_zone_last_15(cur)]),
                }
                cur.close()
            except Exception as e:
                print(e)
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


def api_zone_movement(cur, start = "entrance", end = "exit"):
    try:
        result = cur.sql(f'''SELECT 
        track_id,
        MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) as start_ts,
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) as end_ts,
        strftime(start_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as start,
        strftime(end_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as end
    FROM '/tmp/warehouse_oa/*.parquet'
    GROUP BY track_id
    HAVING MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) IS NOT NULL
    AND MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) IS NOT NULL
    AND MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) < 
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) ORDER BY start_ts DESC LIMIT 15;''').fetchall()

    except:
        return []
    return [(bytes_to_uuid(x[0]), str(x[3]), str(x[4])) for x in result]


def api_zone_last_15(cur):
    try:
        result = cur.sql('''SELECT track_id, event_ts as _event_ts, strftime(event_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as event_ts, event_name, track_conf, track_class FROM '/tmp/warehouse_oa/*.parquet' ORDER BY _event_ts DESC LIMIT 15;''').fetchall()
    except:
        return []
    return [(bytes_to_uuid(x[0]), str(x[1]), str(x[2]), str(x[3]), str(x[4])) for x in result]

@app.get("/cam.jpg")
def video_feed():
    return fs.get_stream()  # type: ignore

args: Args = None # type:ignore 


class ApiProcess():
    def __init__(self, 
            _args: Args
        ):
        global args
    
        args = _args
    
    def start(self):
        uvicorn.run(
            "app.processes.api.api_process:app", host="0.0.0.0", port=8080, log_level="info"
        )
