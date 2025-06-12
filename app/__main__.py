import json
import signal
from threading import Thread
import time

from app.processes import CounterProcess, DbProcess

import multiprocessing
from app.config import TORCH_DEVICE
from app.parse_args import parse_args
from app.utils.logger import get_logger

import torch

from app.utils.mmap import mmap_context, mmap_read_nonblocking, mmap_write
from app.utils.stop_detection import stop_detection

# required for multiprocessing using gpu, see https://pytorch.org/docs/stable/notes/multiprocessing.html#cuda-in-multiprocessing
# must stay at the top
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")


def handler(signum, frame):
    pass


signal.signal(signal.SIGINT, handler)


def main():
    motd()
    args = parse_args()
    logger = get_logger(__name__)
    logger.info("Starting communication")

    server_stopped = multiprocessing.Event()
    logger.info("Spawning counter process")
    counter_process = CounterProcess(args, server_stopped)

    thread = Thread(target=wait_for_reset, args=(server_stopped, True))
    thread.daemon = True
    thread.start()

    logger.info("Spawning sync process")
    db_process = DbProcess(args, server_stopped)
    db_process.start()
    
    counter_process.start()

    def stop_server(*args2):
        stop_detection("CTRL+C", {}, True)

    signal.signal(signal.SIGUSR2, stop_server)

    thread.join()
    
    logger.info("counter_process join")
    counter_process.join(3)
    logger.info("db_process join")
    db_process.join(10)
    logger.info("counter_process terminate")
    counter_process.terminate()
    logger.info("db_process terminate")
    db_process.terminate()
    logger.info("Bye !")
    os.kill(os.getpid(), signal.SIGKILL)


import os


def wait_for_reset(server_stopped, true):
    try:
        with mmap_context(
            "/tmp/stop_detection.json", 512000
        ) as shared_memory_stop_detection:
            stop_detection_bytes = mmap_read_nonblocking(
                shared_memory_stop_detection
            )
            print("/tmp/stop_detection.json content: ", stop_detection_bytes)
        os.remove("/tmp/stop_detection.json")
        print("/tmp/stop_detection.json removed")
    except Exception as e:
        print(e)
    while True:
        try:
            with mmap_context(
                "/tmp/stop_detection.json", 512000
            ) as shared_memory_stop_detection:
                while True:
                    try:
                        stop_detection_bytes = mmap_read_nonblocking(
                            shared_memory_stop_detection
                        )
                        if stop_detection_bytes:
                            stop_detection = json.loads(
                                stop_detection_bytes.decode(encoding="utf-8")
                            )

                            mmap_write(shared_memory_stop_detection, 512000, bytes([]))

                            print(json.dumps(stop_detection, indent=4))
                            
                            time.sleep(0.1)
                            
                            server_stopped.set()

                            if not stop_detection["fast_reload"]:
                                print("!!! MAJOR ERROR !!!")
                            else:
                                print("Restarting detection")

                            return

                    except Exception as a:
                        print(a)

                    time.sleep(1 / 33)
        except:
            time.sleep(1 / 33)
            pass


def motd():
    red = "\x1b[31;20m"
    reset = "\x1b[0m"
    bold = "\x1b[37;1m"
    bold_red = "\x1b[31;1m"
    # fmt: off
    print('                                                      ')
    print(f'   {red}              ((##(              {bold_red}   OA Tracker')
    print(f'   {red}        ((((((((((##(((((        {reset}      ')
    print(f'   {red}     (((((             ##(((     {bold}       ')
    print(f'   {red}   ((((,           ((((  /(((#   {reset}      ')
    print(f'   {red}  #(((            ((((((   ((((  {reset}      ')
    print(f'   {red} *(((             (#((((    (((  {reset}      ')
    print(f'   {red} #(((                       (((( {reset}      ')
    print(f'   {red} *#((                       (((  {bold}   PyTorch info:')
    print(f'   {red}  #(((                     #((#  {reset}     Version: {torch.__version__}')
    print(f'   {red}   (((#(                 #((((   {reset}     Device: {TORCH_DEVICE} {("MPS available") if hasattr(torch.backends, "mps") and torch.backends.mps.is_built() else ""} {("CUDA available") if hasattr(torch.backends, "cuda") and torch.backends.cuda.is_built() else ""}')
    print(f'   {red}     #(((#,           /#((((     {reset}      ')
    print(f'   {red}        #((((((###(((((((        {reset}      ')
    print(f'   {red}              *#(#,              {reset}      ')
    print('                                                      ')
    # fmt: on


# init
if __name__ == "__main__":
    main()
