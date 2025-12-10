from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timezone
import os

from business_logic.metamessage import AssistantMessage, Conversation
from utils.jsonl_logger import JsonlLogger
from utils.queued_logger import QueuedLogger


def test_chat_webhook_success(tmp_path):
    chat_data = {
        "event": "message_created",
        "id": 123,
        "content": "Hello assistant!",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "message_type": "incoming",
        "conversation": {
            "id": 456,
            "status": "open",
            "inbox_id": "inbox123",
        },
        "sender": {
            "id": 789,
            "name": "Test User",
            "email": "test@example.com",
        },
        "account": {
            "id": 321,
            "name": "Test Account",
        },
    }

    local_storage_data = {
        "hello": {
            "tags": ["greeting"],
            "priority": "normal",
            "type": "text",
            "response": "Hello! How can I help you today?",
        }
    }

    mock_storage_instance = MagicMock()
    mock_storage_instance.__enter__.return_value = local_storage_data
    mock_storage_instance.__exit__.return_value = None
    os.environ["LOCAL_STORAGE"] = str(Path(f"{tmp_path}/storage.json"))

    JsonlLogger(file_path=Path(f"{tmp_path}/chat_training_data.jsonl"))
    QueuedLogger(file_path=Path(f"{tmp_path}/data.jsonl"))

    mock_conversation_instance = Conversation(
        id=456,
        status="open",
        inbox_id="inbox123"
    )

    mock_last_message = AssistantMessage(
        content="Hello! How can I help you today?",
        tags=["greeting"],
        priority="normal",
        msg_type="text",
        role="knowledge_storage"
    )

    mock_conversation_instance.messages.append(mock_last_message)

    with patch(
            "webhooks.routers.askai.LocalStorage", return_value=mock_storage_instance
        ) as mock_storage_class, \
        patch(
            "webhooks.routers.askai.RedisClient.fetch_conversation",
            new_callable=AsyncMock,
        ) as mock_fetch, \
        patch(
            "webhooks.routers.askai.RedisClient.save_conversation",
            new_callable=AsyncMock,
        ) as mock_save, \
        patch(
            "webhooks.routers.askai.VLLMClient.send_message",
            return_value=("Hi! How can I help you today?", ["greeting"], "normal", "text"),
        ) as mock_llm, \
        patch(
            "webhooks.routers.askai.JsonlLogger.log_pair",
            new_callable=AsyncMock,
        ) as mock_jsonl_log:

            mock_jsonl_log.log_pair = None
    
            mock_fetch.return_value = mock_conversation_instance
    
            from main import app
            client = TestClient(app, raise_server_exceptions=True)
            response = client.post("/assistant_bot/chat", json=chat_data)

    assert response.status_code == 200

    resp = response.json()
    assert resp["response_message"] == "Hello! How can I help you today?"
    assert resp["tags"] == ["greeting"]
    assert resp["priority"] == "normal"
    assert resp["msg_type"] == "text"

    mock_storage_class.assert_called_once()
    mock_storage_instance.__enter__.assert_called_once()
    mock_fetch.assert_called_once()
    mock_save.assert_called_once()
    mock_llm.assert_not_called()
    mock_jsonl_log.assert_called_once()

