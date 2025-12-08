from collections import Counter
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass, field

class MessageTypeEnum(Enum):
    '''All message types'''
    AUTORIZATION = "авторизация"
    PAYMENT = "опллата"
    BUG = "баги"
    FAQ = "вопросы по функционалу"

class MessagePriorityEnum(Enum):
    '''All priorities'''
    CRITICAL = "критический"
    HIGH = "высокий"
    AVERAGE = "средний"
    LOW = "низкий"

class MessageRoleEnum(str, Enum):
    '''All roles, they are used strictly internally'''
    USER = "user"
    ASSISTANT = "assistant" #referes to the LLM
    KNOWLEDGE_BASE = "knowledge_base"

class MessageTag:
    '''An entity for tags in the messages'''
    name: str = field()

@dataclass
class UserMessage:
    '''An entity for users' messages'''
    id: int
    name: str
    email: str
    content: str
    role: str

@dataclass
class AssistantMessage:
    '''An entity for assistants' messages'''
    content: str
    msg_type: str
    tags: list[str]
    priority: str
    role: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @classmethod
    def from_tuple(cls, data: tuple) -> 'AssistantMessage':
        msg_type, priority, tags, text = data
        return cls(
            content=text,
            msg_type=msg_type,
            priority=priority,
            tags=tags,
            role=MessageRoleEnum.ASSISTANT.value
        )

    def __post_init__(self):
        if isinstance(self.msg_type, MessageTypeEnum):
            self.msg_type = self.msg_type.value

        if isinstance(self.priority, MessagePriorityEnum):
            self.priority = self.priority.value

        if isinstance(self.role, MessageRoleEnum):
            self.role = self.role.value

@dataclass
class Conversation:
    '''
    An aggregator that handles all conversation-related bussiness logic.

    Attributes:
        id (int): Id of the conversation.
        status (str): Status of the conversation. Comes from an external service.
        inbox_id (str): Inbox id of the conversation. Comes from an external service.
        messages (list[AssistantMessage | UserMessage]): All messages.
    '''
    id: int = field()
    status: str = field()
    inbox_id: str | None = field()

    messages: list[AssistantMessage | UserMessage] = field(default_factory=list)

    def precompute_meta(
        self, 
        message: str, 
        storage: dict[str, dict], 
        created_at: datetime | None = None
    ) -> AssistantMessage | None:
        '''Handles priority, type, tags.

        Manages priority, type, tags from given storage. Parses the given message into keywords and tries to find the most commmon matches in the storage.

        Args:
            message (str): User's message.
            storage (dict[str, dict]): Dict or json structure as a dict.
            created_at (datetime | None): Time of assistant's message creation.

        Returns:
            AssistantMessage | None: The most common match from the storage.
        '''

        words = message.lower().split()

        priority_counter = Counter()
        type_counter = Counter()
        response_counter = Counter()
        tags_set: set[str] = set()

        for keyword in words:
            meta = storage.get(keyword)
            if meta:
                priority_counter[meta["priority"]] += 1
                type_counter[meta["type"]] += 1
                response_counter[meta["response"]] += 1
                tags_set.update(meta["tags"])

        if not priority_counter:
            return None

        priority = priority_counter.most_common(1)[0][0]
        msg_type = type_counter.most_common(1)[0][0]
        response = response_counter.most_common(1)[0][0]

        return AssistantMessage(
            content=response,
            msg_type=msg_type,
            tags=list(tags_set),
            priority=priority,
            role=MessageRoleEnum.KNOWLEDGE_BASE.value,
            created_at=created_at #type: ignore
        )    


    def add_message(self, message: AssistantMessage | UserMessage) -> None:
        '''Appends messages to the conversation'''
        self.messages.append(message)

