import asyncio
from contextlib import asynccontextmanager
import json
import multiprocessing
import os
import queue
import time
from typing import Any
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette import EventSourceResponse

import uvicorn
from app.parse_args import Args
from app.processes.api.frame_streamer import FrameStreamer

from fastapi.middleware.cors import CORSMiddleware

from app.utils.logger import get_logger


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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    asyncio.create_task(handle_counter_events())
    #asyncio.create_task(request_counts())
    yield

app = FastAPI(lifespan=lifespan)


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
    return True


# the only route returning html
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html.jinja", {"request": request, "dashboard_data": {}})  # type: ignore


# server side event route streaming data from the detector
queue_sse_event: queue.Queue[dict[str, Any]] = queue.Queue()

client_last_presence = 0 
@app.get("/dashboard/sse")
async def message_stream(request: Request):
    async def event_generator():
        global client_last_presence
        while True:
            client_last_presence = time.time()
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            once = True
            event = None
            while event or once:
                once = False
                await asyncio.sleep(0.01)
                try:
                    event = queue_sse_event.get_nowait()
                except:
                    break
                now_time = time.time() * 1000
                if event:
                    try:
                        yield {
                            "id": now_time,
                            "retry": 15000,
                            "data": json.dumps(event),
                        }
                    except Exception as err:
                        logger.error(event)
                        logger.error(err)

    return EventSourceResponse(event_generator())


# camera feed jpg is a streaming response route lazily loading the last image we have from the detector
fs = FrameStreamer()
camera_loop_duration = 33.33333 # 30 fps
@app.get("/cam.jpg")
def video_feed():
    return fs.get_stream(freq=int(1 / camera_loop_duration))  # type: ignore


@app.get("/cam/play")
def video_play():
    detection_input_queue.put({"event": "set_paused", "value": False})


# route to get data of all detectors between two timestamps
queue_counter: queue.Queue[dict[str, Any]] = queue.Queue()
last_to_dashboard: float = 0
@app.get("/cam/collect")
def collect_counter_data(to: float, _from=Query(alias="from")):
    global queue_counter
    global last_to_dashboard

    _from = float(_from)

    if _from >= to:
        return HTTPException(status_code=400, detail="From must be smaller than to")

    if to - _from < 1000:
        return HTTPException(
            status_code=400,
            detail=f"Duration must exceed one second, from: {_from} to: {to} duration: {to - _from}",
        )

    now = time.time() * 1000

    if to > now or _from > now:
        return HTTPException(status_code=400, detail="To and from must be in the past")

    id = time.time()

    last_to_dashboard = to

    detection_input_queue.put(
        {"event": f"get_count", "from": _from, "to": to, "id": id}
    )

    event = None
    while True:
        try:
            event = queue_counter.get_nowait()
            if event["id"] == id:
                break
        except:
            pass
        time.sleep(0.01)

    event.pop("id")
    event.pop("event")

    return event

# pauses the detection process sending the camera
@app.get("/cam/pause")
def video_pause():
    detection_input_queue.put({"event": "set_paused", "value": True})


# show the overlay over the camera image
@app.get("/cam/show_overlay")
def video_show_overlay():
    detection_input_queue.put(
        {"event": "set_hide_overlay", "value": False}
    )


# remove the overlay over the camera image
@app.get("/cam/hide_overlay")
def video_hide_overlay():
    detection_input_queue.put(
        {"event": "set_hide_overlay", "value": True}
    )



async def request_counts():
    global detection_input_queues
    while True:
        i = 0
        await asyncio.sleep(0.2)

        try:
            detection_input_queue.put({
                "event": "get_count_for_dashboard",
                "from": last_to_dashboard,
                "to": time.time() * 1000,
            })
        except Exception as err:
            logger.error(err)
            pass

        i = i + 1



no_client = True
no_client_last_sent = 0
async def handle_counter_events():
    global detection_output_queue
    global detection_input_queue
    global client_last_presence
    global no_client
    global no_client_last_sent
    while True:
        once = True
        event = None
        if time.time() - no_client_last_sent > 1:
            no_client_last_sent = time.time()
            detection_input_queue.put(
                {"event": "set_dashboard", "value": not no_client}
            )
        if time.time() - client_last_presence > 3:
            no_client = True
        else:
            no_client = False
        while event or once:
            once = False
            await asyncio.sleep(0.01)
            try:
                event = detection_output_queue.get_nowait()
            except:
                break
            if event:
                if event["event"] == f"crash":
                    os._exit(1)
                if event["event"] == f"count":
                    queue_counter.put(event)
                    continue
                if event["event"] == f"visualization":
                    fs.send_detection(event["value"])
                else:
                    queue_sse_event.put(event)


detection_output_queue: multiprocessing.Queue = None # type: ignore
detection_input_queue: multiprocessing.Queue = None # type: ignore
args: Args = None # type:ignore 

def start_api_process(
    _detection_output_queue: multiprocessing.Queue,
    _detection_input_queue: multiprocessing.Queue,
    _args: Args
):
    global detection_output_queue
    global detection_input_queue
    global args
    
    detection_output_queue = _detection_output_queue
    detection_input_queue = _detection_input_queue
    args = _args

    uvicorn.run(
        "app.processes.api.api_process:app", host="0.0.0.0", port=8000, log_level="info"
    )
