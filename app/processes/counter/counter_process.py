import multiprocessing
from app.counters import ZoneCounter, Counter
from app.parse_args import Args
from app.processes.counter.detection_loop import CounterLoop
from multiprocessing.synchronize import Event as EventClass


all_counters: list[type[Counter]] = [
    ZoneCounter
    # add counters here
]


class CounterProcess(multiprocessing.Process):
    def __init__(self, args: Args, server_stopped: EventClass):
        global all_counters
        multiprocessing.Process.__init__(self, name=f"Counter")
        self.args = args
        self.server_stopped = server_stopped

    def run(self) -> None:
        detection_loop = CounterLoop(self.args, all_counters, self.server_stopped)
        detection_loop.start()
        print("counter stop")
