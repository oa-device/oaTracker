import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock, ANY
from http.server import BaseHTTPRequestHandler
from app.api.request_handler import RequestHandler, start_server
from app.utils.person_counter import PersonCounter
from app.vision.track import track
import json
import time
from io import BytesIO
import threading


class TestRequestHandler(RequestHandler):
    def __init__(self, instance_config):
        self.instance_config = instance_config
        self.headers = {}
        self.wfile = BytesIO()
        self.rfile = BytesIO()

    def send_response(self, code):
        self.status_code = code

    def send_header(self, name, value):
        self.headers[name] = value

    def end_headers(self):
        pass


@pytest.fixture(params=["video.mp4", "video2.mp4"])
def mock_handler(request):
    instance_config = {"name": f"test_instance_{request.param}", "camera": os.path.expanduser(f"~/Downloads/{request.param}"), "api_port": 8000}
    return TestRequestHandler(instance_config)


@pytest.fixture(scope="module", params=["video.mp4", "video2.mp4"])
def setup_tracking(request):
    # Start tracking in a separate thread
    tracking_thread = threading.Thread(
        target=track,
        args=(os.path.expanduser(f"~/Downloads/{request.param}"),),
        kwargs={"instance_name": f"test_instance_{request.param}", "loop_video": True},
    )
    tracking_thread.start()

    # Wait for some data to be processed
    time.sleep(5)

    yield

    # Clean up (TODO: implement a way to stop the tracking thread)
    # For now, we'll let the thread run until the test session ends


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/cam/collect?from={}&to={}", 200, {"count": 0}),
        ("/cam/collect", 400, {"error": "Missing required parameters: 'from' and 'to'"}),
        ("/cam/collect?from={}&to={}", 400, {"error": "Invalid time range"}),
    ],
)
def test_handle_cam_collect(mock_handler, setup_tracking, path, expected_status, expected_response):
    current_time = int(time.time() * 1000)
    from_time = current_time - 60000  # 1 minute ago
    to_time = current_time

    if "from={}&to={}" in path:
        if expected_status == 400:
            # For invalid time range test
            path = path.format(to_time, from_time)
        else:
            path = path.format(from_time, to_time)

    mock_handler.path = path
    mock_handler.handle_cam_collect()

    assert mock_handler.status_code == expected_status
    response = json.loads(mock_handler.wfile.getvalue().decode())

    if expected_status == 200:
        assert "count" in response
        assert isinstance(response["count"], int)
    else:
        assert response == expected_response


@patch("app.utils.person_counter.PersonCounter.get_counter")
def test_handle_cam_collect_no_data(mock_get_counter, mock_handler):
    mock_get_counter.return_value = None
    mock_handler.path = "/cam/collect?from=1&to=2"
    mock_handler.handle_cam_collect()

    assert mock_handler.status_code == 404
    assert json.loads(mock_handler.wfile.getvalue().decode()) == {"error": "No data available for the specified camera"}


@patch("app.api.request_handler.HTTPServer")
def test_start_server(mock_http_server):
    instance_config = {"name": "test_instance", "camera": os.path.expanduser("~/Downloads/video.mp4"), "api_port": 8000}
    start_server(instance_config)
    mock_http_server.assert_called_once_with(("", 8000), ANY)
    assert issubclass(mock_http_server.call_args[0][1], BaseHTTPRequestHandler)
    mock_http_server.return_value.serve_forever.assert_called_once()


# This line tells pytest to ignore the TestRequestHandler class when collecting tests
TestRequestHandler.__test__ = False

if __name__ == "__main__":
    pytest.main()
