import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime


class CloudCompatibleFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if isinstance(record.msg, dict):
            log_data["message"] = record.msg
        else:
            log_data["message"] = record.getMessage()

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logger(log_dir="logs", level=logging.INFO):
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)

    formatter = CloudCompatibleFormatter()
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


root_logger = setup_logger()


def get_logger(name):
    return logging.getLogger(name)
