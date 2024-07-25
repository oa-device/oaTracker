from http.server import BaseHTTPRequestHandler, HTTPServer
import json

latest_detections = []


# Handles HTTP requests and returns the latest detection results for GET requests to /detections
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/detections":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            global latest_detections
            # Pretty-print JSON response
            pretty_json = json.dumps(latest_detections, indent=4)
            self.wfile.write(pretty_json.encode())
        else:
            self.send_response(302)
            self.send_header("Location", "/detections")
            self.end_headers()


# Starts the HTTP server on the specified port number
def start_server(port_number):
    server_address = ("", port_number)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Starting server on port {port_number}")
    httpd.serve_forever()
