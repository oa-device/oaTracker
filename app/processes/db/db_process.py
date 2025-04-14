import multiprocessing
import threading
import time

from app.processes.db.flight_server import DuckDBFlightServer

def stop_thread(server, server_stopped, process):
    server_stopped.wait()
    server.on_close()
    
class DbProcess(multiprocessing.Process):
    def __init__(self, args, server_stopped):
        multiprocessing.Process.__init__(self, name=f"Db")
        self.server_stopped = server_stopped
        print("Starting DuckDB Flight server on 0.0.0.0:8815")

    def run(self) -> None:
        server = DuckDBFlightServer()
        message_thread = threading.Thread(target=stop_thread, args=(server, self.server_stopped, self))
        message_thread.start()
        server.serve()
