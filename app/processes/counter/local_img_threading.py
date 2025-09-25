import threading
import time
import os
import glob
from typing import Literal, Tuple, Union

from app.utils.logger import get_logger
import cv2

import numpy.typing as Numpy
import numpy as np

from app.utils.stop_detection import major_error

logger = get_logger(__name__)


from collections import deque


class LocalImgThreading:
    """
    A class collecting frames from local folder on a
    secondary thread
    ...

    Attributes
    ----------

    __width: int
        Image output width
    __height: int
        Image output height
    __started: bool
        True if the thread was started
    __queue: collections.deque
        Queue holding the collected frames
    __thread: threading.Thread
        The executing thread
    __folder_path: str
        Path to the folder containing images

    Methods
    -------
    start()
        Starts the thread

    stop()
        Stops the thread

    read()
        Returns an image from the queue, same return type as cv2.VideoCapture.read()

    __update()
        This function is the main loop for the thread, picks latest image and adds it to the queue


    """

    def __init__(self, folder_path="/tmp/webcam/") -> None:
        self.__folder_path = folder_path
        self.__started = False
        self.__queue: deque[Numpy.NDArray[np.uint8]] = deque(maxlen=2)

    def start(self) -> None:
        """Starts the thread"""
        if self.__started:
            print("[!] Threaded local image capturing has already been started.")
            return None
        self.__started = True
        self.__img_thread = threading.Thread(
            name="LocalImg",
            target=self.__update_img,
            args=(),
        )
        self.__img_thread.start()
        logger.info("Local image capture thread started")

    def stop(self) -> None:
        """Stops the thread"""
        self.__started = False
        self.__img_thread.join()

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
                    e = Exception("Local image timed out while reading from image thread queue")
                    major_error(self.camId, "Local image timed out while reading from image thread queue", e)
                    raise e

    def isOpened(self):
        return os.path.exists(self.__folder_path)

    def __get_latest_image(self) -> Union[None, str]:
        """Gets the latest image file from the folder and deletes older ones"""
        try:
            if not os.path.exists(self.__folder_path):
                os.mkdir(self.__folder_path)

            # Get all image files from the folder - WebP first, then JPG as fallback
            webp_files = glob.glob(os.path.join(self.__folder_path, '*.webp'))
            jpg_files = glob.glob(os.path.join(self.__folder_path, '*.jpg'))

            # Prefer WebP for efficiency, but support JPG for compatibility
            image_files = webp_files + jpg_files

            if not image_files:
                return None

            # Sort by modification time (newest first)
            image_files.sort(key=os.path.getmtime, reverse=True)

            # Get the latest file
            latest_file = image_files[0]

            # Delete all other files
            for file_path in image_files[1:]:
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # Ignore errors when deleting files

            return latest_file

        except Exception:
            return None

    def __update_img(self) -> None:
        """This function is the main loop for the img thread, picks latest image and adds it to the queue"""
        i = 0
        while self.__started:
            try:
                latest_image_path = self.__get_latest_image()

                if latest_image_path and os.path.exists(latest_image_path):
                    frame = cv2.imread(latest_image_path)
                    if frame is not None:
                        i = 0
                        resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)
                        self.__queue.append(resized_frame)
                        # Delete the image after processing
                        try:
                            os.remove(latest_image_path)
                        except OSError:
                            pass  # Ignore errors when deleting files
                    else:
                        time.sleep(0.05)  # Wait a bit if image couldn't be read
                else:
                    time.sleep(0.05)  # Wait a bit if no images found

            except Exception:
                i += 1
                if i >= 25:
                    e = Exception("Local image timed out in image thread")
                    major_error(self.camId, "Local image timed out in image thread", e)
                    raise e
                time.sleep(0.05)