import json
import logging
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from datetime import datetime, timezone

LOG_FILE_PATH = Path("data.jsonl")

class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "level": getattr(record, "levelname", None),
            "time": self.formatTime(record),
            "message": getattr(record, "msg", None),
        }

        if getattr(record, "levelno", None) == logging.ERROR:
            entry.update({"type": getattr(record, "ext_type", None)})

        extra = getattr(record, "extra_data", None)
        if extra: entry.update({"extra": extra})

        return json.dumps(entry, ensure_ascii=False)


class QueuedLogger:
    '''
    An async-safe logger wrapper. Utilizes a queue to avoid holding event loop.

    Attributes:
        _instance ("QueuedLogger | None"): Attribute for singleton implementation.
    '''

    _instance: "QueuedLogger | None" = None

    def __new__(cls, file_path: Path = LOG_FILE_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, file_path: Path = LOG_FILE_PATH):
        if getattr(self, "_initialized", False):
            return

        self.file_path = file_path

        self.queue = Queue()

        self.file_handler = logging.FileHandler(
            self.file_path, encoding="utf-8", mode="a"
        )
        self.file_handler.setFormatter(JsonlFormatter())

        self.listener = QueueListener(self.queue, self.file_handler)

        self.logger = logging.getLogger("queued_logger")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(QueueHandler(self.queue))

        self._initialized = True

    async def startup(self):
        '''Starts the background thread listener'''
        self.listener.start()

    async def shutdown(self):
        '''Flushes and stops listener'''
        self.listener.stop()

    def error(self, message: str, exc: Exception, extra=None):
        '''Omits error level logs.

        A dedicated method for logging on the error level.

        Args:
            message (str): Message of the error.
            exc (Exception): The error instance itself.
            extra (dict): Additional fields.
        '''
        self.logger.error(
            msg=message,
            extra={
                "time": datetime.now(tz=timezone.utc).isoformat,
                "ext_type": exc.__class__.__name__,
                "extra_data": extra or {},
            },
        )
