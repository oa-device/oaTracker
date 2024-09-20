#!/usr/bin/env python
"""Defines the FrameStreamer class and it's interface with the in memory SQLite datebase
"""

import asyncio
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

class FrameStreamer:
    """The FrameStreamer class allows you to send frames and visualize them as a stream"""

    def __init__(self):
        self.frame: bytearray = None # type: ignore 
        self.event = asyncio.Event()

    def send_detection(self, img: bytearray):
        self.frame = bytearray(img)
        self.event.set()

    async def _start_stream(self, freq: int = 30):
        """Continuous loop to stream the frame from SQLite to html image/jpeg format

        Args:
            img_id (str): ID (primary key) of the image in the DB
            freq (int, optional): Loop frequency. Defaults to 30.

        Yields:
            bytes: HTML containing the bytes to plot the stream
        """
        try:
            while True:
                img = None
                if self.event:
                    await self.event.wait()
                    self.event.clear()
                else:
                    await asyncio.sleep(1 / freq)
                try:
                    img = self.frame
                except:
                    pass

                if not img:
                    continue
                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + img + b"\r\n"
                )
        except asyncio.CancelledError:
            return

    def get_stream(
        self,
        freq: int = 30,
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
            self._start_stream(freq),
            media_type="multipart/x-mixed-replace;boundary=frame",
            status_code=status_code,
            headers=headers,
            background=background,
        )
