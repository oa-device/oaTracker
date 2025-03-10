import json
from typing import Any
from app.utils.mmap import mmap_context, mmap_write


def stop_detection(message: str, data: Any, fast_reload=False):
    with mmap_context("/tmp/stop_detection.json", 512000) as shared_memory_img:
        mmap_write(
            shared_memory_img,
            512000,
            bytes(
                json.dumps(
                    {"message": message, "data": data, "fast_reload": fast_reload}
                ).encode("utf-8")
            ),
        )


def major_error(message: str, error: Any):
    stop_detection(f"Major error: ${message}", str(error), False)
