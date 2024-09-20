import multiprocessing
from app.config import TORCH_DEVICE
from app.parse_args import parse_args
from app.utils.logger import get_logger


from app.processes.api.api_process import start_api_process
from app.processes.counter.counter_process import start_counter_process

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
    queue_all_events_counter_output: multiprocessing.Queue = multiprocessing.Queue()
    queue_all_events_counter_input: multiprocessing.Queue = multiprocessing.Queue()


    logger.info("Spawning counter process")
    start_counter_process(
        queue_all_events_counter_output,
        queue_all_events_counter_input,
        args
    )

    logger.info("Start API process")
    start_api_process(
        queue_all_events_counter_output,
        queue_all_events_counter_input,
        args
    )


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
