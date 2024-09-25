import logging
import os

from colorama import Fore, Style

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()


class CustomFormatter(logging.Formatter):
    grey = Fore.LIGHTBLACK_EX + "%(levelname)s:\x1b[0m \t  %(message)s"
    yellow = Fore.RED + "%(levelname)s:\x1b[0m \t  %(message)s"
    red = Fore.RED + "%(levelname)s:\x1b[0m \t  %(message)s"
    green = Fore.GREEN + "%(levelname)s:\x1b[0m \t  %(message)s"
    bold_red = Style.BRIGHT + Fore.RED + "%(levelname)s:\x1b[0m \t  %(message)s"
    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger("JPR_People_Counter")
logger.setLevel(LOGLEVEL)

ch = logging.StreamHandler()
ch.setLevel(LOGLEVEL)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)
