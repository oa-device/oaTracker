import asyncio
from contextlib import asynccontextmanager
import json
import mmap
import multiprocessing
from multiprocessing import synchronize
import os
import queue
import signal
import time
from typing import Any, Callable
from fastapi import APIRouter, FastAPI, Query, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette import EventSourceResponse

import uvicorn
from app.parse_args import Args
from app.processes.api.frame_streamer import FrameStreamer

from fastapi.middleware.cors import CORSMiddleware

from app.utils.logger import get_logger
from app.utils.mmap import mmap_context, mmap_read, pathname_state, pathname_img, get_shared_memory_path


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

running = True

@asynccontextmanager
async def lifespan(_app: FastAPI):
    asyncio.create_task(handle_counter_events())
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

# server side event route streaming data from the detector
client_last_presence = 0 
@app.get("/dashboard/sse")
async def message_stream(_request: Request):
    async def event_generator():
        global client_last_presence, running
        shared_memory_path = get_shared_memory_path('state.shm')
        with mmap_context(shared_memory_path, 64000) as shared_memory_state:
            while running:
                try:
                    client_last_presence = time.time()
                    body = await mmap_read(shared_memory_state)
                    yield {
                        "id": time.time(),
                        "retry": 15000,
                        "data": body.decode('utf-8'),
                    }
                except Exception as e:
                    print(e)
                await asyncio.sleep(0.0333)

    return EventSourceResponse(event_generator())



@app.get("/cam.jpg")
def video_feed():
    return fs.get_stream()  # type: ignore


@app.get("/cam/play")
def video_play():
    detection_input_queue.put({"event": "set_paused", "value": False})


# route to get data of all detectors between two timestamps
queue_counter: queue.Queue[dict[str, Any]] = queue.Queue()
last_to_dashboard: float = 0
@app.get("/cam/collect")
def collect_counter_data(to: float, _from=Query(alias="from")):
    global queue_counter, running, last_to_dashboard

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

    event: dict[str, Any] = None # type: ignore
    while running:
        try:
            event = queue_counter.get_nowait()
            if event["id"] == id:
                break
        except Exception:
            pass
        time.sleep(0.0001)

    if event:
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
    global detection_input_queues, running
    while running:
        i = 0
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


async def handle_counter_events():
    global detection_input_queue, running, client_last_presence
    no_client = True
    no_client_last_sent = 0
    while running:
        now=time.time()
        no_client_before = not not no_client
        if now - client_last_presence > 0.5:
            no_client = True
        else:
            no_client = False
        if (no_client_before is not no_client) or now - no_client_last_sent > 1:
            no_client_last_sent = now
            detection_input_queue.put(
                {"event": "set_dashboard", "value": not no_client}
            )
        await asyncio.sleep(0.1)


detection_input_queue: multiprocessing.Queue = None # type: ignore
args: Args = None # type:ignore 


class ApiProcess():
    def __init__(self, 
            _args: Args, _detection_input_queue: multiprocessing.Queue
        ):
        global detection_input_queue
        global args
    
        detection_input_queue = _detection_input_queue
        args = _args
    
    def start(self):
        uvicorn.run(
            "app.processes.api.api_process:app", host="0.0.0.0", port=8000, log_level="info"
        )
