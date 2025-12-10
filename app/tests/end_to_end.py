from datetime import datetime, timezone
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from main import app
from utils.local_storage import LocalStorage
from llm.vllm_client import VLLMClient

storage_file = Path(__file__).parent.parent / "storage.json"

LocalStorage._storage_path = str(storage_file.resolve())
vllm = VLLMClient()

chat_data = {
    "event": "message_created",
    "id": 123,
    "content": "Подскажи какое сейчас время.",
    "created_at": datetime.now(tz=timezone.utc).isoformat(),
    "message_type": "incoming",
    "conversation": {
        "id": 456,
        "status": "open",
        "inbox_id": "inbox123"
    },
    "sender": {
        "id": 789,
        "name": "Test User",
        "email": "test@example.com"
    },
    "account": {
        "id": 321,
        "name": "Test Account"
    }
}

def test_end_to_end():
    with TestClient(app) as client:
        response = client.post("/assistant_bot/chat", json=chat_data)
        assert response.status_code == 200
        print("Actual response", response.json())
        assert response.json() != {'response_message': '', 'tags': [], 'priority': 'низкий', 'msg_type': 'вопросы по функционалу'} # LLM did manage to produce a correct json response
    

