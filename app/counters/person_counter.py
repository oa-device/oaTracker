

from app.counters import GenericCounter


class PersonCounter(GenericCounter):
    name="person_counter"
    def __init__(self, args):
        super().__init__(args, PersonCounter.name, 0)