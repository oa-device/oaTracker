import threading
import time
from typing import Literal, Tuple, Union

from app.utils.logger import get_logger
import cv2

import numpy.typing as Numpy
import numpy as np

from app.utils.stop_detection import major_error

logger = get_logger(__name__)


from collections import deque


class VideoCaptureThreading:
    """
    A class collecting frames on a
    secondary thread
    ...

    Attributes
    ----------

    __width: int
        Camera output width
    __height: int
        Camera output height
    __started: bool
        True if the thread was started
    __queue: collections.deque
        Queue holding the collected frames
    __cap: cv2.VideoCapture
        OpenCV video capture class
    __thread: threading.Thread
        The executing thread

    Methods
    -------
    start()
        Starts the thread

    stop()
        Stops the thread

    read()
        Returns an image from the queue, same return type as cv2.VideoCapture.read()

    __set_cap()
        Initializes OpenCV's video capture

    __update()
        This function is the main loop for the thread, picks a frame and adds it the the queue


    """

    def __init__(self, camId: str, width=736, height=552 ) -> None:
        self.__width = width
        self.__height = height
        self.__cap: cv2.VideoCapture = None  # type: ignore
        self.__set_cap()
        self.__started = False
        self.__queue: deque[Numpy.NDArray[np.uint8]] = deque(maxlen=2)

        self.camId = camId

    def start(self) -> None:
        """Starts the thread"""
        if self.__started:
            print("[!] Threaded video capturing has already been started.")
            return None
        self.__started = True
        self.__cam_thread = threading.Thread(
            name="Cam",
            target=self.__update_cam,
            args=(),
        )
        self.__cam_thread.start()
        logger.info("Video capture thread started")

    def stop(self) -> None:
        """Stops the thread"""
        self.__started = False
        self.__cam_thread.join()

    def read(
        self,
    ) -> Union[
        Tuple[Literal[True], Numpy.NDArray[np.uint8]], Tuple[Literal[False], None]
    ]:
        """Returns an image from the queue, same return type as cv2.VideoCapture.read()"""
        i = 0
        while True:
            try:
                frame = self.__queue.popleft()
                i = 0
                return (True, frame)
            except Exception:
                time.sleep(0.01)
                i += 1
                if i >= 100:
                    e = Exception("Camera timed out while reading from camera thread queue")
                    major_error(self.camId, "Camera timed out while reading from camera thread queue", e)
                    raise e

    def isOpened(self):
        return self.__cap.isOpened() if self.__cap is not None else False

    def __set_cap(self) -> None:
        """Initializes OpenCV's video capture"""
        try:
            if hasattr(self, "__cap") and self.__cap is not None:
                self.__cap.release()

            self.__cap = cv2.VideoCapture(0)
            self.__cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.__width)
            self.__cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__height)
        except Exception:
            e = ValueError("Error setting capture")
            major_error(self.camId, "Error setting capture", e)
            raise e

    def __update_cam(self) -> None:
        """This function is the main loop for the cam thread, picks a frame and adds it the the raw queue"""
        i = 0
        while self.__started:
            try:
                grabbed, frame = self.__cap.read()
                if grabbed:
                    i = 0
                    self.__queue.append(
                        cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)
                    )  # type: ignore
            except Exception:
                i += 1
                if i >= 20:
                    self.__set_cap()
                if i >= 25:
                    e = Exception("Camera timed out in camera thread")
                    major_error(self.camId, "Camera timed out in camera thread", e)
                    raise e
                pass
