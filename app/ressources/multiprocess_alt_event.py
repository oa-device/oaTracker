from contextlib import AbstractContextManager
import multiprocessing

from multiprocessing.synchronize import Event as MultiprocessingEvent
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

class MultiprocessAltEvent:
    """
    A class creating two context managers
    allowing two processes to execute
    one after the other

    Attributes
    ----------
    event_context_manager_0 : MultiprocessAltEventContextManager
        Content manager for the first process

    event_context_manager_1 : MultiprocessAltEventContextManager
        Content manager for the second process

    __event_0 : Event
        Event for the first process (do not use directly)

    __event_1 : Event
        Event for the second process (do not use directly)


    Methods
    ----------
    start(): None
        Starts the chain reaction
    """

    def __init__(self) -> None:
        logger.debug("Starting multiprocess alt event")
        self.__event_0 = multiprocessing.Event()
        self.__event_1 = multiprocessing.Event()
        self.event_context_manager_0 = MultiprocessAltEventContextManager(
            0, self.__event_0, self.__event_1
        )
        self.event_context_manager_1 = MultiprocessAltEventContextManager(
            1, self.__event_1, self.__event_0
        )

    def start(self) -> None:
        self.__event_0.set()


class MultiprocessAltEventContextManager(AbstractContextManager):
    """
    A context manager to allow two process to execute one at a time
    using two Event
    ...

    Attributes
    ----------
    __event : multiprocessing.Event
        Event for the current process (do not use directly)
    __other_event : multiprocessing.Event
        Event for the other process (do not use directly)
    """

    def __init__(
        self,
        process_id: int,
        event: MultiprocessingEvent,
        other_event: MultiprocessingEvent,
    ) -> None:
        super().__init__()
        self.__event = event
        self.__other_event = other_event
        self.__process_id = process_id

    def __enter__(self) -> None:
        print(f'Waiting for process {self.__process_id} to finish')
        self.__event.wait()

    def __exit__(self, _exc_type: Any, _exc_value: Any, _tb: Any) -> None:
        self.__event.clear()
        self.__other_event.set()
