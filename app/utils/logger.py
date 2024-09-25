import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
import time
from pygments import highlight, lexers, formatters


class CloudCompatibleFormatter(logging.Formatter):

        
    def format(self, record):
        log_data = {
            "level": record.levelname,
            "message": self.format_message(record),
            "timestamp": self.formatTime(record, self.datefmt),
            "epoch_ms": int(time.time() * 1000),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return maybe_json_color(json.dumps(log_data), hasattr(self, 'colors'))

    def setColors(self):
        self.colors = True

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

def maybe_json_color(json: str, color: bool):
    if not color:
        return json
    
    return highlight(json, lexers.JsonLexer(), formatters.TerminalFormatter()).rstrip()

def setup_logger(log_dir="logs", level=logging.INFO, file_only=False):
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)

    file_handler_formatter = CloudCompatibleFormatter()
    file_handler.setFormatter(file_handler_formatter)
    file_handler.setLevel(level)

    logger.addHandler(file_handler)

    if not file_only:
        console_handler_formatter = CloudCompatibleFormatter()
        console_handler_formatter.setColors()
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_handler_formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger


root_logger = setup_logger()


def get_logger(name):
    return logging.getLogger(name)


# Helper function to create structured log messages
def create_log_message(**kwargs):
    return json.dumps(kwargs)
