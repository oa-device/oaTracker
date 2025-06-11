import asyncio
import json
import time
import traceback
from typing import Callable
import uuid
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import functools
import yaml
from sse_starlette import EventSourceResponse
from pyarrow import flight
import uvicorn
from .frame_streamer import FrameStreamer


from fastapi.middleware.cors import CORSMiddleware

from api.logger import get_logger
import duckdb


duckdb_con = duckdb.connect()

# Allow these origins to access the API
origins = ["http://localhost:8000", "http://localhost:3000", "http://localhost:8080"]

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


def connect_with_retry(max_attempts=5):
    for attempt in range(max_attempts):
        try:
            client = flight.connect("grpc://localhost:8815")
            return client
        except FlightUnavailableError:
            if attempt < max_attempts - 1:
                print(
                    f"Connection attempt {attempt + 1} failed, retrying in 1 second..."
                )
                time.sleep(1)
            else:
                raise


client = connect_with_retry()


def execute_query(query):
    global client
    try:
        ticket = flight.Ticket(query.encode("utf-8"))
        reader = client.do_get(ticket)
        result = reader.read_all().to_pylist()
        return result
    except Exception as e:
        print(f"Query error: {str(e)}")
        client = connect_with_retry()
        return None


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
    return True


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html.jinja", {"request": request, "dashboard_data": {}})  # type: ignore


@app.get("/stats", response_class=HTMLResponse)
async def minute_statistics_page(request: Request):
    return templates.TemplateResponse(
        "minute_statistics.html.jinja", {"request": request}
    )


@app.get("/edit_config", response_class=HTMLResponse)
async def config_editor(request: Request):
    return templates.TemplateResponse("config/index.html.jinja", {"request": request})  # type: ignore


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

        return json.dumps({"ok": True})
    print(request)


client_last_presence = 0


@app.get("/dashboard/sse")
async def message_stream(start: str = "entrance", end: str = "exit"):
    async def event_generator():
        global client_last_presence
        while True:
            try:
                    
                client_last_presence = time.time()
                yield {
                    "id": str(client_last_presence),
                    "retry": 15000,
                    "data": json.dumps(
                        [
                            [],  # api_zone_movement(cur, start, end),
                            [],  # api_zone_last_15(cur),
                            api_last_seen_from(),
                            api_first_seen_from(),
                            api_mean_dwell(),
                            api_total_presence(),
                            api_presence_last_15_seconds(),
                        ]
                    ),
                }
            except Exception as e:
                tbe = traceback.TracebackException.from_exception(e)
                stack_frames = traceback.extract_stack()
                tbe.stack.extend(stack_frames)
                formatted_traceback = "".join(tbe.format())
                print(f"Formatted Traceback:\n{formatted_traceback}")
                print('sse', e)
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


def api_zone_movement(start="entrance", end="exit"):
    try:
        return []
        result = execute_query(
            f"""SELECT 
        track_id,
        MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) as start_ts,
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) as end_ts,
        strftime(start_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as start,
        strftime(end_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as end
    FROM zone_events
    GROUP BY track_id
    HAVING MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) IS NOT NULL
    AND MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) IS NOT NULL
    AND MIN(CASE WHEN event_name = 'enter_zone_{start}' THEN event_ts END) < 
        MAX(CASE WHEN event_name IN ('enter_zone_{end}', 'leave_zone_{end}') THEN event_ts END) ORDER BY start_ts DESC LIMIT 15;"""
        )

    except Exception:
        return []
    return [(bytes_to_uuid(x[0]), str(x[3]), str(x[4])) for x in result]


def api_zone_last_15():
    return []
    try:
        result = execute_query(
            """SELECT track_id, event_ts as _event_ts, strftime(event_ts, '%Y-%m-%dT%H:%M:%S.%g+00:00') as event_ts, event_name, track_conf, track_class FROM zone_events ORDER BY _event_ts DESC LIMIT 15;"""
        )
    except Exception:
        return []
    return [
        (bytes_to_uuid(x[0]), str(x[1]), str(x[2]), str(x[3]), str(x[4]))
        for x in result
    ]


def api_last_seen_from():
    try:
        result = execute_query(
            """WITH last_events AS (
            SELECT t.track_id, t.event_name
            FROM zone_events t
            INNER JOIN (
                SELECT track_id, MAX(event_ts) as max_ts
                FROM zone_events
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
        )[0]
        
        return result
        
    except Exception:
        return {
        "last_seen_zone_out_top_left": "",
        "last_seen_zone_out_door_right": "",
        "last_seen_zone_out_door_left": "",
        "last_seen_zone_out_bottom_right": "",
        "last_seen_zone_out_bottom": ""
    }


def api_first_seen_from():
    try:
        result = execute_query(
            """
            WITH first_events AS (
                SELECT t.track_id, t.event_name
                FROM zone_events t
                INNER JOIN (
                    SELECT track_id, MIN(event_ts) as max_ts
                    FROM zone_events
                    GROUP BY track_id
                ) m ON t.track_id = m.track_id AND t.event_ts = m.max_ts
            )
            SELECT 
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_top_left' THEN 1 END) as first_seen_zone_out_top_left,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_door_right' THEN 1 END) as first_seen_zone_out_door_right,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_door_left' THEN 1 END) as first_seen_zone_out_door_left,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_bottom_right' THEN 1 END) as first_seen_zone_out_bottom_right,
                COUNT(CASE WHEN event_name LIKE 'enter_zone_out_bottom' THEN 1 END) as first_seen_zone_out_bottom FROM first_events;"""
        )[0]
        
        return result


    except Exception as e:
        print(e)
        return {
            "first_seen_zone_out_top_left": "",
            "first_seen_zone_out_door_right": "",
            "first_seen_zone_out_door_left": "",
            "first_seen_zone_out_bottom_right": "",
            "first_seen_zone_out_bottom": ""
        }

def api_mean_dwell():
    try:
        result = execute_query(
            """
            WITH DwellTimes AS (
    SELECT
        track_id,
        MIN(event_ts) AS start_time,
        MAX(event_ts) AS end_time,
        (EPOCH(MAX(event_ts)) - EPOCH(MIN(event_ts))) AS dwell_time_seconds
    FROM zone_events
    GROUP BY track_id
)
SELECT
    AVG(dwell_time_seconds) AS mean_dwell_time_seconds
FROM DwellTimes;"""
        )[0]["mean_dwell_time_seconds"]

    except Exception:
        return 0
    return result


def api_total_presence():
    try:
        result = execute_query(
            """
            WITH DwellTimes AS (
        SELECT
            track_id,
            EPOCH(MAX(event_ts)) - EPOCH(MIN(event_ts)) AS dwell_time_seconds
        FROM zone_events
        GROUP BY track_id
    )
    SELECT
        COUNT(DISTINCT track_id) AS total_track_count,
        SUM(dwell_time_seconds) AS total_time_spent_seconds
    FROM DwellTimes;"""
        )[0]
        
        return [result["total_track_count"], result["total_time_spent_seconds"]]

    except Exception as e:
        print(e)
        return []


def api_presence_last_15_seconds():
    try:
        result = execute_query(
            """SELECT
            COUNT(DISTINCT track_id) as presence_last_15_seconds
            FROM zone_events WHERE event_ts AT TIME ZONE 'UTC' > current_timestamp - INTERVAL '15 seconds';"""
        )[0]["presence_last_15_seconds"]

    except Exception as e:
        print("api_presence_last_15_seconds", e)
        return []
    return result


def api_minute_statistics(minutes=1):
    """Get detection statistics for the last N minutes"""
    try:
        # First check if we have data
        check_result = execute_query(
            """SELECT COUNT(*) FROM zone_events LIMIT 1;"""
        )

        has_data = check_result and check_result[0][0] > 0

        if not has_data:
            print("No data found")
            # Try another way to get the data - directly from the live tracking
            return {
                "timestamp": time.time(),
                "total_people": 0,
                "total_detections": 0,
                "first_seen": "",
                "last_seen": "",
            }

        # Continue with the regular query
        result = execute_query(
            f"""
            WITH MinuteDetections AS (
                SELECT 
                    track_id,
                    COUNT(*) as detection_count,
                    MIN(event_ts) as first_seen,
                    MAX(event_ts) as last_seen
                FROM zone_events
                WHERE event_ts AT TIME ZONE 'UTC' > current_timestamp - INTERVAL '{minutes} minutes'
                GROUP BY track_id
            )
            SELECT 
                COUNT(DISTINCT track_id) as total_people,
                SUM(detection_count) as total_detections,
                strftime(MIN(first_seen), '%Y-%m-%dT%H:%M:%S.%g+00:00') as first_seen,
                strftime(MAX(last_seen), '%Y-%m-%dT%H:%M:%S.%g+00:00') as last_seen
            FROM MinuteDetections;
        """
        )[0]

        return {
            "timestamp": time.time(),
            "total_people": result[0] if result[0] is not None else 0,
            "total_detections": result[1] if result[1] is not None else 0,
            "first_seen": result[2],
            "last_seen": result[3],
        }
    except Exception as e:
        print(f"Error getting minute statistics: {e}")
        try:
            # Fallback to events table if reading fails
            return {
                "timestamp": time.time(),
                "total_people": 0,
                "total_detections": 0,
                "first_seen": "",
                "last_seen": "",
            }
        except Exception as inner_e:
            print(f"Error in fallback for minute statistics: {inner_e}")
            return {
                "timestamp": time.time(),
                "total_people": 0,
                "total_detections": 0,
                "first_seen": None,
                "last_seen": None,
                "error": str(e),
            }


@app.get("/api/stats")
async def minute_statistics(minutes: int = 1):
    """Endpoint to get detection statistics for the last N minutes"""
    result = api_minute_statistics(minutes)
    return result


@app.get("/cam.jpg")
def video_feed():
    return fs.get_stream()  # type: ignore


config = uvicorn.Config(
    app, host="0.0.0.0", port=8080, log_level="info", loop="asyncio"
)
server = uvicorn.Server(config=config)
server.run()
