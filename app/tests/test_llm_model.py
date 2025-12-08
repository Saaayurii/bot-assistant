import json
import httpx
import http
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def mock_httpx_client():
    fake_text = {"content": "Привет!", "tags": ["greeting"], "type": "вопросы по функционалу", "priority": "низкий"}
    fake_response = {
            "choices": 
                [
                    {
                        "text": json.dumps(fake_text)
                    }
                ]
            }

    mock_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                            http.HTTPStatus.OK, content=json.dumps(fake_response)
                        )
                )
        )

    return mock_client

@pytest.fixture
def safe_test_logging(tmp_path):
    from utils.queued_logger import QueuedLogger
    QueuedLogger(file_path=Path(f"{tmp_path}/data.jsonl"))

@pytest.fixture
def mock_vllm_client(safe_test_logging):
    fake_model_url = "http://localhost:8000"
    fake_model_path = "models/llm"

    from llm.vllm_client import VLLMClient
    VLLMClient._instance = None
    client = VLLMClient(server_url=str(fake_model_url), model_path=fake_model_path)
    return client

@pytest.mark.asyncio
async def test_send_message_returns_metadata_tuple(mock_vllm_client, mock_httpx_client):
    conversation = [
        {"role": "system", "content": "You are a helper"},
        {"role": "assistant", "content": "Hello!"}
    ]

    with patch("llm.vllm_client.httpx.AsyncClient", return_value=mock_httpx_client):
        msg_type, priority, tags, content = await mock_vllm_client.send_message("How are you doing?", conversation)

    assert msg_type == "вопросы по функционалу"
    assert priority == "низкий"
    assert tags == ["greeting"]
    assert content == "Привет!"

