import json
import yaml
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import time

from app.utils.shared_state import latest_detections, get_unique_object_counts, camera_info, get_input_source
from app.utils.person_counter import PersonCounter
from app.utils.logger import get_logger, create_log_message

logger = get_logger(__name__)

# Load configuration
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# CORS settings
CORS_SETTINGS = config.get("cors", {})
ALLOWED_ORIGINS = CORS_SETTINGS.get("allowed_origins", [])
ALLOWED_METHODS = CORS_SETTINGS.get("allowed_methods", [])
ALLOWED_HEADERS = CORS_SETTINGS.get("allowed_headers", [])


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, instance_config, *args, **kwargs):
        self.instance_config = instance_config
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)

        logger.info(
            create_log_message(
                event="http_request", method="GET", path=self.path, client_address=self.client_address[0], instance=self.instance_config["name"]
            )
        )

        if parsed_path.path == "/detections":
            self.handle_detections()
        elif parsed_path.path == "/cam/collect":
            self.handle_cam_collect()
        elif parsed_path.path == "/health":
            self.handle_health()
        else:
            self.send_error(404)
            logger.warning(create_log_message(event="http_not_found", path=self.path, instance=self.instance_config["name"]))

    def handle_detections(self):
        query_params = parse_qs(urlparse(self.path).query)
        from_seconds = query_params.get("from", [None])[0]

        if from_seconds is not None:
            try:
                from_seconds = int(from_seconds)
                if 1 <= from_seconds <= 30:
                    object_counts = get_unique_object_counts(from_seconds, self.instance_config["name"])
                    self.send_json_response(object_counts)
                else:
                    self.send_error(400, "Invalid 'from' parameter. Must be between 1 and 30.")
            except ValueError:
                self.send_error(400, "Invalid 'from' parameter. Must be an integer.")
        else:
            self.send_json_response(latest_detections.get(self.instance_config["name"], []))

    def handle_cam_collect(self):
        query_params = parse_qs(urlparse(self.path).query)
        to_ms = query_params.get("to", [None])[0]
        from_ms = query_params.get("from", [None])[0]

        logger.info(create_log_message(event="cam_collect_request", from_ms=from_ms, to_ms=to_ms, instance=self.instance_config["name"]))

        if None in (to_ms, from_ms):
            logger.warning(
                create_log_message(event="cam_collect_invalid_params", from_ms=from_ms, to_ms=to_ms, instance=self.instance_config["name"])
            )
            self.send_error(400, "Missing required parameters: 'from' and 'to'")
            return

        try:
            to_seconds = float(to_ms) / 1000
            from_seconds = float(from_ms) / 1000
            now = time.time()

            logger.debug(
                create_log_message(
                    event="cam_collect_time_conversion",
                    from_seconds=from_seconds,
                    to_seconds=to_seconds,
                    now=now,
                    instance=self.instance_config["name"],
                )
            )

            if from_seconds >= to_seconds:
                logger.warning(
                    create_log_message(
                        event="cam_collect_invalid_time_range",
                        from_seconds=from_seconds,
                        to_seconds=to_seconds,
                        instance=self.instance_config["name"],
                    )
                )
                self.send_error(400, "Invalid time range")
                return

            if to_seconds > now:
                logger.warning(
                    create_log_message(event="cam_collect_future_time", to_seconds=to_seconds, now=now, instance=self.instance_config["name"])
                )
                self.send_error(400, "End time must be in the past")
                return

            input_source = self.instance_config["camera"]
            person_counter = PersonCounter.get_counter(self.instance_config["name"])

            if person_counter is None:
                logger.warning(create_log_message(event="cam_collect_no_counter", input_source=input_source, instance=self.instance_config["name"]))
                self.send_error(404, "No data available for the specified camera")
                return

            count = person_counter.get_count(from_seconds, to_seconds)

            logger.info(
                create_log_message(
                    event="cam_collect_success",
                    input_source=input_source,
                    from_seconds=from_seconds,
                    to_seconds=to_seconds,
                    count=count,
                    instance=self.instance_config["name"],
                )
            )
            self.send_json_response({"count": count})
        except ValueError as e:
            logger.error(
                create_log_message(event="cam_collect_value_error", from_ms=from_ms, to_ms=to_ms, error=str(e), instance=self.instance_config["name"])
            )
            self.send_error(400, "Invalid parameters")
        except Exception as e:
            logger.error(
                create_log_message(event="cam_collect_error", error=str(e), from_ms=from_ms, to_ms=to_ms, instance=self.instance_config["name"])
            )
            self.send_error(500, f"Internal server error: {str(e)}")

    def handle_health(self):
        instance_name = self.instance_config["name"]
        input_source = get_input_source(instance_name)
        person_counter = PersonCounter.get_counter(instance_name)
        latest_detection = latest_detections.get(instance_name, [])

        is_tracking = person_counter is not None and bool(latest_detection)

        try:
            if latest_detection and isinstance(latest_detection, list):
                last_detection = latest_detection[-1]  # Get the last item in the list
                last_detection_time = last_detection.get("timestamp") if isinstance(last_detection, dict) else None
            else:
                last_detection_time = None
        except Exception as e:
            logger.error(create_log_message(event="health_check_error", error=str(e), instance=instance_name))
            last_detection_time = None

        health_status = {
            "status": "healthy" if is_tracking else "degraded",
            "instance": instance_name,
            "timestamp": int(time.time()),
            "input_source": input_source,
            "tracking_status": "active" if is_tracking else "inactive",
            "person_counter_available": person_counter is not None,
            "last_detection_time": last_detection_time,
        }

        # Log the health status
        logger.info(create_log_message(event="health_check", health_status=health_status, instance=instance_name))

        self.send_json_response(health_status)

    def send_cors_headers(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", ", ".join(ALLOWED_METHODS))
        self.send_header("Access-Control-Allow-Headers", ", ".join(ALLOWED_HEADERS))

    def send_json_response(self, data, status_code=200):
        try:
            self.send_response(status_code)
            self.send_header("Content-type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        except BrokenPipeError:
            logger.warning(create_log_message(event="broken_pipe_error", instance=self.instance_config["name"]))
        except Exception as e:
            logger.error(create_log_message(event="send_json_response_error", error=str(e), instance=self.instance_config["name"]))

    def send_error(self, code, message=None):
        try:
            self.send_response(code)
            self.send_header("Content-type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            if message:
                self.wfile.write(json.dumps({"error": message}).encode())
        except BrokenPipeError:
            logger.warning(create_log_message(event="broken_pipe_error", instance=self.instance_config["name"]))
        except Exception as e:
            logger.error(create_log_message(event="send_error_response_error", error=str(e), instance=self.instance_config["name"]))


def start_server(instance_config):
    port_number = instance_config["api_port"]
    server_address = ("", port_number)

    class InstanceRequestHandler(RequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(instance_config, *args, **kwargs)

    httpd = HTTPServer(server_address, InstanceRequestHandler)
    logger.info(create_log_message(event="server_start", port=port_number, instance=instance_config["name"]))
    httpd.serve_forever()
