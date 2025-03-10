import multiprocessing
from app.parse_args import Args
from app.processes.sync.sync_loops import SyncLoops
from multiprocessing.synchronize import Event as EventClass


class SyncProcess(multiprocessing.Process):
    def __init__(self, args: Args, server_stopped: EventClass):
        self.args = args
        self.server_stopped = server_stopped
        multiprocessing.Process.__init__(self, name=f"Sync")

    def run(self) -> None:
        sync_loops = SyncLoops(self.args, self.server_stopped)
        sync_loops.start()
        print("sync_loops stop")
