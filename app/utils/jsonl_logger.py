import json
import logging
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from typing import List

JSONL_LOG_FILE_PATH = Path("chat_training_data.jsonl")

class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "user": getattr(record, "user", None),
            "assistant": getattr(record, "assistant", None),
            "tags": getattr(record, "tags", []),
            "type": getattr(record, "msg_type", None),
            "priority": getattr(record, "priority", None),
            "sender": getattr(record, "sender", "assistant"),
        }
        return json.dumps(payload, ensure_ascii=False)
    

class JsonlLogger:
    '''
    An async-safe logger that saves conversations' data in jsonl formant.
    Afterwards, the data is supposed to be used for LLM's tuning.

    Attributes:
        _instance ("JsonlLogger | None"): Attribute for singleton implementation
    '''

    _instance: "JsonlLogger | None" = None

    def __new__(cls, file_path: Path = JSONL_LOG_FILE_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, file_path: Path = JSONL_LOG_FILE_PATH):
        if getattr(self, "_initialized", False):
            return

        self.file_path = file_path

        self.queue = Queue()

        self.file_handler = logging.FileHandler(
            self.file_path, encoding="utf-8", mode="a"
        )
        self.file_handler.setFormatter(JsonlFormatter())

        self.listener = QueueListener(self.queue, self.file_handler)

        self.logger = logging.getLogger("jsonl_logger")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(QueueHandler(self.queue))

        self._initialized = True

    async def startup(self):
        """Starts the background thread listener."""
        self.listener.start()

    async def shutdown(self):
        """Flushs and stops listener."""
        self.listener.stop()

    async def log_pair(
        self,
        user_message: str,
        assistant_message: str,
        tags: List[str],
        msg_type: str,
        priority: str,
        sender: str = "assistant"
    ):
        """Async-safe log call."""
        self.logger.info(
            "",
            extra={
                "user": user_message,
                "assistant": assistant_message,
                "tags": tags,
                "msg_type": msg_type,
                "priority": priority,
                "sender": sender
            }
        )
