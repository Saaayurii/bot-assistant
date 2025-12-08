import os
from typing import Any

from redis.asyncio import Redis, ConnectionPool

from utils.queued_logger import QueuedLogger
from utils.serialize_adapter import SerializeAdapter

# we should get rid of it 
from business_logic.metamessage import Conversation, AssistantMessage, UserMessage

logger = QueuedLogger()

class RedisClient:
    '''
    A high-level async redis client. Stores users' conversations with the LLM.

    Attributes:
        _instance ('RedisClient | None'): Attribute for singleton implementation.
    '''

    _instance: 'RedisClient | None' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        serialize_adapter: SerializeAdapter | None = None
    ):
        if getattr(self, "_initialized", False):
            return

        self.host = os.environ.get("REDIS_HOST") or host
        self.port = os.environ.get("REDIS_PORT") or port
        self.db = db
        self.password = password or os.environ.get("REDIS_PASSWORD")
        self.serializer = serialize_adapter

        self.pool: ConnectionPool | None = None
        self.client: Redis | None = None

        self._initialized = True

    def _ensure_connection(self):
        '''Ensures whether a connection to the redis exists'''
        if self.client is None or self.pool is None:
            if self.password:
                self.pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    max_connections=20
                )
            else:
                self.pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True,
                    max_connections=20
                )
            self.client = Redis(connection_pool=self.pool)

    async def hset(self, name: str, key: str, value: Any) -> int:
        '''Hset wrapper'''
        self._ensure_connection()
        serialized = self.serializer.serialize(value) if self.serializer else value
        return await self.client.hset(name, key, serialized)

    async def hget(self, name: str, key: str, dtos: list[type] | None = None) -> Any | None:
        '''Hget wrapper'''
        self._ensure_connection()
        raw = await self.client.hget(name, key)
        if not raw:
            return None
        try:
            return self.serializer.deserialize(raw, dtos=dtos) if self.serializer else raw
        except Exception:
            return None

    async def fetch_conversation(self, user_id: str, conv_id: str) -> Conversation | None:
        '''Fetches a conversation from redis.

        Fetches a conversation from redis with user's id as a name and conversation's id as a key.

        Args:
            user_id (str): Id of the user.
            conv_id (str): Id of the conversation.

        Returns:
            Conversation | None: Optionally conversation.
        '''
        key = f"conv:{conv_id}"
        name = f"user:{user_id}"
        return await self.hget(name, key, dtos=[Conversation, AssistantMessage, UserMessage])

    async def save_conversation(self, user_id: str, conv_id: str, conversation: "Conversation") -> int:
        '''Saves a conversation in redis.

        Saves or updates a conversation pydantic model in redis with key as a conversation id and name as a user's id.

        Args:
            user_id (str): Id of the user.
            conv_id (str): Id of the conversation.
            conversation ("Conversation"): Pydantic model with all messages.

        Returns:
            int: Amount of inserted records.
        '''
        key = f"conv:{conv_id}"
        name = f"user:{user_id}"
        return await self.hset(name, key, conversation)

    async def close(self):
        if self.client:
            await self.client.aclose()
        if self.pool:
            await self.pool.disconnect()

