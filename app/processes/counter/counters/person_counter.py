

from app.processes.counter.counters.generic_counter import GenericCounter


class PersonCounter(GenericCounter):
    def __init__(self):
        super().__init__(f"Person counter", 0)