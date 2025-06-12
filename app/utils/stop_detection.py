import json
import time
from typing import Any
from app.utils.mmap import mmap_context, mmap_read_nonblocking, mmap_write


headers = {
    "Content-Type": "application/x-www-form-urlencoded",
}


def stop_detection(message: str, data: Any, fast_reload=False):
    # try:
    #     requests.post('http://ntfy.sh/seetrus_error_l0fqfug7acp4pq2wf76183lq6tnv0773', headers=headers, data=f"{message}: {data}", timeout=1)
    # except:
    #     pass

    with mmap_context("/tmp/stop_detection.json", 512000) as shared_memory_img:
        stop_detection_bytes = mmap_read_nonblocking(shared_memory_img)
        if not stop_detection_bytes:
            with open(f"/tmp/stop_detection-{int(time.time() * 1000)}.json", "w") as f:
                f.write(
                   json.dumps(
                        {"message": message, "data": data, "fast_reload": fast_reload}
                    )
                )

            mmap_write(
                shared_memory_img,
                512000,
                bytes(
                    json.dumps(
                        {"message": message, "data": data, "fast_reload": fast_reload}
                    ).encode("utf-8")
                ),
            )
        else:
            print("Already dead")


def major_error(camId: str, message: str, error: Any):
    stop_detection(f"{camId} Major error: {message}", str(error), False)
