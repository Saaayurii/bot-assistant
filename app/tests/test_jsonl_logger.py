import asyncio
import json
import pytest
import pytest_asyncio
from utils.jsonl_logger import JsonlLogger

@pytest_asyncio.fixture
async def logger(tmp_path):
    JsonlLogger._instance = None
    log_file = tmp_path / "test_log.jsonl"
    logger = JsonlLogger(file_path=log_file)
    await logger.startup()
    yield logger
    await logger.shutdown()
    if log_file.exists():
        log_file.unlink()

@pytest.mark.asyncio
async def test_log_pair_creates_entry(logger):
    user_msg = "Hello"
    assistant_msg = "Hi!"
    tags = ["greeting"]
    msg_type = "вопросы по функционалу"
    priority = "низкий"

    await logger.log_pair(user_msg, assistant_msg, tags, msg_type, priority)

    await asyncio.sleep(0.05)

    lines = logger.file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["user"] == user_msg
    assert entry["assistant"] == assistant_msg
    assert entry["tags"] == tags
    assert entry["type"] == msg_type
    assert entry["priority"] == priority
    assert entry["sender"] == "assistant"

@pytest.mark.asyncio
async def test_multiple_pairs(logger):
    for i in range(5):
        await logger.log_pair(
            f"user {i}", 
            f"assistant {i}", 
            tags=[f"tag{i}"], 
            msg_type="вопросы по функционалу", 
            priority="низкий"
        )

    await asyncio.sleep(0.05)

    lines = logger.file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5

    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert entry["user"] == f"user {i}"
        assert entry["assistant"] == f"assistant {i}"
        assert entry["tags"] == [f"tag{i}"]
        assert entry["type"] == "вопросы по функционалу"
        assert entry["priority"] == "низкий"
        assert entry["sender"] == "assistant"

@pytest.mark.asyncio
async def test_shutdown_flushes_queue(tmp_path):
    log_file = tmp_path / "test_log.jsonl"
    JsonlLogger._instance = None
    logger = JsonlLogger(file_path=log_file)
    await logger.startup()

    await logger.log_pair(
        user_message="last user",
        assistant_message="last assistant",
        tags=["final"],
        msg_type="вопросы по функционалу",
        priority="низкий"
    )
    await logger.shutdown()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["user"] == "last user"
    assert entry["assistant"] == "last assistant"
    assert entry["tags"] == ["final"]

