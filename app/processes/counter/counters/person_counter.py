

from app.processes.counter.counters.generic_counter import GenericCounter


class PersonCounter(GenericCounter):
    def __init__(self):
        super().__init__(0)
        self.name = f"Person counter"