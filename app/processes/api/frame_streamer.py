#!/usr/bin/env python
"""Defines the FrameStreamer class and it's interface with the in memory SQLite datebase
"""

import asyncio
import os
from pathlib import Path
import threading
import time
from typing import Any, Mapping, Union
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import logging

from app.utils.mmap import mmap_context, mmap_read_nonblocking
from app.utils.mmap import pathname_img, mmap_context


loading_cam_filepath = os.path.normpath(Path(__file__).parent / "loading_cam.jpg")
logger = logging.getLogger(__name__)


class FrameStreamer:
    """The FrameStreamer class allows you to send frames and visualize them as a stream"""

    def __init__(self):
        self.running = True
        with open(loading_cam_filepath, "rb") as loading_cam_file:
            self.img = loading_cam_file.read()
        self.__thread = threading.Thread(
            name=f"Read_img_on_disk",
            target=self.__update,
            args=(),
        )
        self.__thread.start()

    def __update(self):
        while self.running:
            try:
                with mmap_context(pathname_img(), 64000) as shared_memory_img:
                    img = mmap_read_nonblocking(shared_memory_img)
                    if img is not None:
                        self.img = img
                    else:
                        # If no image in shared memory, use loading screen
                        self.img = self.loading_img
            except Exception as e:
                logger.error(f"Frame streamer error: {e}")
                # On error, show loading screen
                self.img = self.loading_img
            time.sleep(0.001)

    async def _start_stream(self):
        """Continuous loop to stream the frame from SQLite to html image/jpeg format
        Yields:
            bytes: HTML containing the bytes to plot the stream
        """
        while self.running:
            try:
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + self.img + b"\r\n")
            except Exception as a:
                pass

            await asyncio.sleep(0.003)

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
