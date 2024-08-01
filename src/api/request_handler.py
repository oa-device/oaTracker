import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from src.utils.shared_state import latest_detections, get_unique_object_counts
import yaml

# Load configuration
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/detections":
            query_params = parse_qs(parsed_path.query)
            from_seconds = query_params.get("from", [None])[0]

            if from_seconds is not None:
                try:
                    from_seconds = int(from_seconds)
                    if 1 <= from_seconds <= 30:
                        object_counts = get_unique_object_counts(from_seconds)

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        response = json.dumps(object_counts)
                        self.wfile.write(response.encode())
                    else:
                        self.send_error(400, "Invalid 'from' parameter. Must be between 1 and 30.")
                except ValueError:
                    self.send_error(400, "Invalid 'from' parameter. Must be an integer.")
            else:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                pretty_json = json.dumps(latest_detections, indent=4)
                self.wfile.write(pretty_json.encode())
        else:
            self.send_response(302)
            self.send_header("Location", "/detections")
            self.end_headers()


def start_server(port_number=None):
    if port_number is None:
        port_number = config["default_server_port"]
    server_address = ("", port_number)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Starting server on port {port_number}")
    httpd.serve_forever()
