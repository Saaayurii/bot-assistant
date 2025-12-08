import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def _RedisClient(tmp_path):
    '''Sets logger's test file path at import time'''
    from utils.queued_logger import QueuedLogger
    QueuedLogger(file_path=Path(f"{tmp_path}/data.jsonl"))
    from utils.redis_storage import RedisClient
    return RedisClient


@pytest.mark.asyncio
async def test_redis_client_singleton(_RedisClient):
    c1 = _RedisClient()
    c2 = _RedisClient()

    assert c1 is c2, "_RedisClient must behave as a singleton"


@pytest.mark.asyncio
async def test_ensure_connection_initializes_only_once(_RedisClient):
    client = _RedisClient(serialize_adapter=None)

    with patch(
        "utils.redis_storage.ConnectionPool"
    ) as mock_pool, patch(
        "utils.redis_storage.Redis"
    ) as mock_redis:
        mock_redis.return_value = AsyncMock()

        client._ensure_connection()
        client._ensure_connection()

        assert mock_pool.call_count == 1
        assert mock_redis.call_count == 1


@pytest.mark.asyncio
async def test_hset_calls_serializer_and_redis(_RedisClient):
    _RedisClient._instance = None
    mock_serializer = MagicMock()
    mock_serializer.serialize.return_value = "serialized-data"

    client = _RedisClient(serialize_adapter=mock_serializer)

    mock_redis = AsyncMock()
    mock_redis.hset = AsyncMock(return_value=1)

    with patch(
        "utils.redis_storage.ConnectionPool"
    ), patch(
        "utils.redis_storage.Redis", return_value=mock_redis
    ):
        result = await client.hset("user:1", "conv:123", {"a": 1})

    mock_serializer.serialize.assert_called_once_with({"a": 1})
    mock_redis.hset.assert_awaited_once_with("user:1", "conv:123", "serialized-data")
    assert result == 1


@pytest.mark.asyncio
async def test_hget_calls_deserializer(_RedisClient):
    _RedisClient._instance = None
    mock_serializer = MagicMock()
    mock_serializer.deserialize.return_value = {"id": 123}

    client = _RedisClient(serialize_adapter=mock_serializer)

    mock_redis = AsyncMock()
    mock_redis.hget = AsyncMock(return_value="raw-data")

    with patch(
        "utils.redis_storage.ConnectionPool"
    ), patch(
        "utils.redis_storage.Redis", return_value=mock_redis
    ):
        from utils.redis_storage import Conversation
        result = await client.hget("user:1", "conv:123", dtos=[Conversation])

    mock_serializer.deserialize.assert_called_once_with("raw-data", dtos=[Conversation])
    assert result == {"id": 123}


@pytest.mark.asyncio
async def test_hget_returns_none_if_empty(_RedisClient):
    _RedisClient._instance = None
    client = _RedisClient(serialize_adapter=None)

    mock_redis = AsyncMock()
    mock_redis.hget = AsyncMock(return_value=None)

    with patch(
        "utils.redis_storage.ConnectionPool"
    ), patch(
        "utils.redis_storage.Redis", return_value=mock_redis
    ):
        result = await client.hget("user:1", "conv:123")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_conversation_calls_hget_correctly(_RedisClient):
    client = _RedisClient(serialize_adapter=AsyncMock())

    with patch.object(
        client, "hget", new_callable=AsyncMock
    ) as mock_hget:
        mock_hget.return_value = "conversation-object"

        result = await client.fetch_conversation("999", "555")

    from utils.redis_storage import Conversation, AssistantMessage, UserMessage
    mock_hget.assert_awaited_once_with(
        "user:999",
        "conv:555",
        dtos=[Conversation, AssistantMessage, UserMessage]
    )
    assert result == "conversation-object"


@pytest.mark.asyncio
async def test_save_conversation_calls_hset_correctly(_RedisClient):
    client = _RedisClient(serialize_adapter=AsyncMock())
    from utils.redis_storage import Conversation
    conversation = Conversation(id=123, status="open", inbox_id="inbox")

    with patch.object(
        client, "hset", new_callable=AsyncMock
    ) as mock_hset:
        mock_hset.return_value = 1

        result = await client.save_conversation("999", "555", conversation)

    mock_hset.assert_awaited_once_with(
        "user:999",
        "conv:555",
        conversation
    )
    assert result == 1
