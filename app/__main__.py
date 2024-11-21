import time
import os

os.environ["CAM_ID"] = "2efdad08-2da0-44bd-8b62-29009bc25389"
os.environ["CAM_BOOT_TS"] = str(time.time()*1000)

from app.processes import ApiProcess, CounterProcess, ProxyDBProcess


import multiprocessing
from app.config import TORCH_DEVICE
from app.parse_args import parse_args
from app.utils.logger import get_logger

import torch


# required for multiprocessing using gpu, see https://pytorch.org/docs/stable/notes/multiprocessing.html#cuda-in-multiprocessing
# must stay at the top
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

def main():
    motd()
    args = parse_args()
    logger = get_logger(__name__)
    logger.info("Starting communication queues")
    queue_all_events_counter_input: multiprocessing.Queue = multiprocessing.Queue()

    logger.info("Spawning DB Proxy process")
    ProxyDBProcess(
        args
    ).start()

    logger.info("Spawning counter process")
    CounterProcess(
        args,
        queue_all_events_counter_input
    ).start()

    logger.info("Spawning API process")
    ApiProcess(
        args,
        queue_all_events_counter_input
    ).start()


def motd():
    red = "\x1b[31;20m"
    reset = "\x1b[0m"
    bold = "\x1b[37;1m"
    bold_red = "\x1b[31;1m"
    # fmt: off
    print(f'                                                      ')
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
    print(f'                                                      ')
    print(f'Dashboard available at http://127.0.0.1:8000/dashboard')
    # fmt: on


# init
if __name__ == "__main__":
    main()
