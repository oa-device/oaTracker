import multiprocessing
import os
import signal
import time
from app.counters import ZoneCounter, Counter
from app.parse_args import Args
from app.processes.counter.counter_loop import CounterLoop


all_counters: list[type[Counter]] = [
    # PersonCounter,
    ZoneCounter
    # add counters here
]

class CounterProcess(multiprocessing.Process):
    def __init__(
        self,
        args: Args
    ):
        multiprocessing.Process.__init__(self, name=f"Counter")
        self.args = args

    def run(self) -> None:
        global all_counters
        counter_loop = CounterLoop(self.args, all_counters)
        def stop_server(*args):
            counter_loop.running = False
            time.sleep(.2)
            os.kill(os.getpid(), signal.SIGTERM)
        signal.signal(signal.SIGINT, stop_server)
        counter_loop.start()
