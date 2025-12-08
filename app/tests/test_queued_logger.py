import asyncio
import json
import pytest
import pytest_asyncio
from utils.queued_logger import QueuedLogger

pytest_plugins = ("pytest_asyncio",)

@pytest_asyncio.fixture
async def logger(tmp_path):
    QueuedLogger._instance = None
    log_file = tmp_path / "test_log.jsonl"
    logger = QueuedLogger(file_path=log_file)
    await logger.startup()
    yield logger
    await logger.shutdown()
    if log_file.exists():
        log_file.unlink()


@pytest.mark.asyncio
async def test_log_exception_creates_entry(logger):
    test_message = "Something went wrong"
    test_exc = ValueError("Invalid value")
    logger.error(
            message=test_message, 
            exc=test_exc, 
            extra={"key": "value"}
        )

    await asyncio.sleep(0.1)

    lines = logger.file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["message"] == test_message
    assert entry["type"] == "ValueError"
    assert entry["extra"] == {"key": "value"}


@pytest.mark.asyncio
async def test_multiple_entries(logger):
    for i in range(5):
        logger.error(f"error {i}", RuntimeError(f"fail {i}"))

    await asyncio.sleep(0.1)

    lines = logger.file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5

    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert entry["message"] == f"error {i}"
        assert entry["type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_shutdown_flushes_queue(tmp_path):
    log_file = tmp_path / "test_log.jsonl"
    QueuedLogger._instance = None
    logger = QueuedLogger(file_path=log_file)
    await logger.startup()

    logger.error("last error", Exception("oops"))
    await logger.shutdown()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["message"] == "last error"

