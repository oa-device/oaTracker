import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
import time


class CloudCompatibleFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "epoch_ms": int(time.time() * 1000),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": self.format_message(record),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def format_message(self, record):
        if isinstance(record.msg, dict):
            return record.msg
        elif isinstance(record.msg, str):
            try:
                return json.loads(record.msg)
            except json.JSONDecodeError:
                return {"text": record.getMessage()}
        else:
            return {"text": str(record.msg)}


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


# Helper function to create structured log messages
def create_log_message(**kwargs):
    return json.dumps(kwargs)
