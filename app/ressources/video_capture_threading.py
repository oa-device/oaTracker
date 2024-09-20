import collections
import threading
from typing import Literal, Tuple, Union
from app.config import IMG_HEIGHT, IMG_WIDTH
from app.utils.logger import get_logger
import cv2

import numpy.typing as Numpy
import numpy as np

logger = get_logger(__name__)

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
        self.__queue: collections.deque[Numpy.NDArray[np.uint8]] = collections.deque(maxlen=2)

        grabbed = False
        frame = None
        
        # get first frame
        while grabbed == False and self.__cap:
            grabbed, frame = self.__cap.read()

        self.__queue.append(frame) # type: ignore

    def start(self) -> None:
        """Starts the thread"""
        if self.__started:
            print("[!] Threaded video capturing has already been started.")
            return None
        self.__started = True
        self.__thread = threading.Thread(
            name=f"Cam",
            target=self.__update,
            args=(),
        )
        self.__thread.start()
        logger.info(
            f"Video capture thread started"
        )

    def stop(self) -> None:
        """Stops the thread"""
        self.__started = False
        self.__thread.join()

    def read(self) -> Union[Tuple[Literal[True], Numpy.NDArray[np.uint8]], Tuple[Literal[False], None]]:
        """Returns an image from the queue, same return type as cv2.VideoCapture.read()"""
        try:
            frame = self.__queue.pop()

            if frame is None:
                print("Warning: empty frame queue")
                return (False, None)

            return (True, frame)
        except Exception as err:
            return (False, None)

    def __set_cap(self) -> None:
        """Initializes OpenCV's video capture"""
        try:
            if hasattr(self, '__cap') and self.__cap is not None:
                self.__cap.release()
            
            self.__cap = cv2.VideoCapture(0)
            self.__cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.__width)
            self.__cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__height)
        except:
            raise ValueError("Error setting capture")

    def __update(self) -> None:
        """This function is the main loop for the thread, picks a frame and adds it the the queue"""
        while self.__started:
            try:
                grabbed, frame = self.__cap.read()
                if grabbed:
                    self.__queue.append(cv2.resize(frame, dsize=(IMG_WIDTH,IMG_HEIGHT))) # type: ignore
                else:
                    self.__set_cap()
            except Exception as err:
                pass
