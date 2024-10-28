import threading
import time
from typing import Literal,  Tuple, Union

from app.utils.logger import get_logger
import cv2

import numpy.typing as Numpy
import numpy as np

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

    def __init__(self, width=640, height=480) -> None:
        self.__width = width
        self.__height = height
        self.__cap: cv2.VideoCapture = None # type: ignore 
        self.__set_cap()
        self.__started = False
        self.__queue: deque[Numpy.NDArray[np.uint8]] = deque(maxlen=2)

        grabbed = False
        frame = None
        
        start=time.monotonic()
        # get first frame
        logger.info('Waiting for camera, timeout is 3 seconds')
        while grabbed == False and self.__cap:
            grabbed, frame = self.__cap.read()
            if time.monotonic() - start > 3:
                raise Exception('Camera timed out')

        self.__queue.append(cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)) # type: ignore

    def start(self) -> None:
        """Starts the thread"""
        if self.__started:
            print("[!] Threaded video capturing has already been started.")
            return None
        self.__started = True
        self.__cam_thread = threading.Thread(
            name=f"Cam",
            target=self.__update_cam,
            args=(),
        )
        self.__cam_thread.start()
        logger.info(
            f"Video capture thread started"
        )

    def stop(self) -> None:
        """Stops the thread"""
        self.__started = False
        self.__cam_thread.join()

    def read(self) -> Union[Tuple[Literal[True], Numpy.NDArray[np.uint8]], Tuple[Literal[False], None]]:
        """Returns an image from the queue, same return type as cv2.VideoCapture.read()"""
        while True:
            try:
                frame = self.__queue.popleft()
                return (True, frame)
            except Exception as err:
                pass

    def __set_cap(self) -> None:
        """Initializes OpenCV's video capture"""
        try:
            if hasattr(self, '__cap') and self.__cap is not None:
                self.__cap.release()
            
            self.__cap = cv2.VideoCapture(0)
            self.__cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.__width)
            self.__cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__height)
        except Exception:
            raise ValueError("Error setting capture")

    def __update_cam(self) -> None:
        """This function is the main loop for the cam thread, picks a frame and adds it the the raw queue"""
        i = 0
        while self.__started:
            i+=1
            try:
                grabbed, frame = self.__cap.read()
                if grabbed:
                    self.__queue.append(cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)) # type: ignore
            except Exception as err:
                if i > 20:
                    self.__set_cap()
                pass
    