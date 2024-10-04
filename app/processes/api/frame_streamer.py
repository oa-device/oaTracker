#!/usr/bin/env python
"""Defines the FrameStreamer class and it's interface with the in memory SQLite datebase
"""

import asyncio
import mmap
from multiprocessing import synchronize
from typing import Any, Mapping, Union
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse

__author__ = "Tiago Prata"
__credits__ = ["Tiago Prata"]
__license__ = "MIT"
__version__ = "0.1.1"
__maintainer__ = "Tiago Prata"
__email__ = "prataaa@hotmail.com"
__status__ = "Beta version"

from app.utils.async_lock import async_lock
from app.utils.mmap import mmap_context, mmap_read
from app.utils.zmipc import ZMClient

import numpy as np  
gfg = np.array((0, 0, 0, 0, 1, 5, 7, 0, 6, 2, 9, 0, 10, 0, 0)) 
  
# without trim parameter 
# returns an array without any trailing  zeros  
  
res = np.trim_zeros(gfg, 'b') 

class Value:
    def __init__(self, value):
        self.value = value
class FrameStreamer:
    """The FrameStreamer class allows you to send frames and visualize them as a stream"""

    def __init__(self, condition: synchronize.Condition):
        self.condition = condition

    async def _start_stream(self):
        # receiver = ZMClient()
        # receiver.add_subscription(topic='img')
        # receiver.execute()
        
        directory = "/dev/shm"
        pathname_img = f"{directory}/cam.shm"
        with mmap_context(pathname_img, 64000) as shared_memory_img:
            """Continuous loop to stream the frame from SQLite to html image/jpeg format
            Yields:
                bytes: HTML containing the bytes to plot the stream
            """
            while True:
                try:
                    img = await mmap_read(shared_memory_img)
                    if not img:
                        await asyncio.sleep(0.0001)
                        continue
                    yield (
                        b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + img + b"\r\n"
                    )
                except Exception as a:
                    await asyncio.sleep(0.0001)
                
                await asyncio.sleep(0.0001)
                


    def get_stream(
        self,
        status_code: int = 206,
        headers: Union[Mapping[str, str], None] = None,
        background: Union[BackgroundTasks, None] = None,
    ) -> StreamingResponse:
        """Get an stream of frames

        Args:
            stream_id (str): ID (primary key) of the stream to be retrieved
            freq (int, optional): Frequency of the continuous loop retrieval (in Hz). Defaults to 30.
            status_code (int, optional): HTTP response status code. Defaults to 206.
            headers (Union[Mapping[str, str], None], optional): HTTP headers. Defaults to None.
            background (Union[BackgroundTasks, None], optional): FastAPI background. Defaults to None.

        Returns:
            StreamingResponse: FastAPI StreamingResponse
        """

        return StreamingResponse(
            self._start_stream(),
            media_type="multipart/x-mixed-replace;boundary=frame",
            status_code=status_code,
            headers=headers,
            background=background,
        )
