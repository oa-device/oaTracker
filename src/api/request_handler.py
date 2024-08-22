import json
import yaml
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from src.utils.shared_state import latest_detections, get_unique_object_counts
from src.utils.person_counter import PersonCounter
from src.utils.logger import get_logger, create_log_message

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
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)

        logger.info(create_log_message(event="http_request", method="GET", path=self.path, client_address=self.client_address[0]))

        if parsed_path.path == "/detections":
            self.handle_detections()
        elif parsed_path.path == "/cam/collect":
            self.handle_cam_collect()
        else:
            self.send_error(404)
            logger.warning(create_log_message(event="http_not_found", path=self.path))

    def handle_detections(self):
        query_params = parse_qs(urlparse(self.path).query)
        from_seconds = query_params.get("from", [None])[0]

        if from_seconds is not None:
            try:
                from_seconds = int(from_seconds)
                if 1 <= from_seconds <= 30:
                    object_counts = get_unique_object_counts(from_seconds)
                    self.send_json_response(object_counts)
                else:
                    self.send_error(400, "Invalid 'from' parameter. Must be between 1 and 30.")
            except ValueError:
                self.send_error(400, "Invalid 'from' parameter. Must be an integer.")
        else:
            self.send_json_response(latest_detections)

    def handle_cam_collect(self):
        query_params = parse_qs(urlparse(self.path).query)
        from_ms = query_params.get("from", [None])[0]
        to_ms = query_params.get("to", [None])[0]
        cam = query_params.get("cam", ["0"])[0]

        if from_ms is None or to_ms is None:
            self.send_error(400, "Invalid parameters")
            return

        try:
            from_seconds = float(from_ms) / 1000
            to_seconds = float(to_ms) / 1000
            person_counter = PersonCounter.get_counter(cam)
            count = person_counter.get_count(from_seconds, to_seconds)

            if count > 0:
                self.send_json_response({"count": count})
            else:
                self.send_json_response({"count": 0, "message": "No data available for the specified time range"}, status_code=404)
        except ValueError:
            self.send_error(400, "Invalid parameters")
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")

    def send_cors_headers(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", ", ".join(ALLOWED_METHODS))
        self.send_header("Access-Control-Allow-Headers", ", ".join(ALLOWED_HEADERS))

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def send_error(self, code, message=None):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        if message:
            self.wfile.write(json.dumps({"error": message}).encode())


def start_server(port_number=None):
    if port_number is None:
        port_number = config["default_server_port"]
    server_address = ("", port_number)
    httpd = HTTPServer(server_address, RequestHandler)
    logger.info(create_log_message(event="server_start", port=port_number))
    httpd.serve_forever()
