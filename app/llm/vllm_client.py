import os
import httpx
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.exceptions import OutputParserException

from utils.queued_logger import QueuedLogger
from exceptions import MissingModelPathException, VllmFailedAllRetriesException

logger = QueuedLogger()

class MessageSchema(BaseModel):
    content: str
    tags: list[str]
    type: str
    priority: str

parser = PydanticOutputParser(pydantic_object=MessageSchema)

class VLLMClient:
    '''
    HTTP client to communicate with LLM on a remote server. Has been designed to work with vLLM's OpenAI-compatible server.

    Attributes:
        _instance ("VLLMClient | None"): Attribute for singleton implementation.
    '''
    _instance: "VLLMClient | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, server_url: str | None = None, model_path: str | None = None):
        if getattr(self, "_initialized", False):
            return

        self.prompt_template = PromptTemplate(
            input_variables=["context", "user_message"],
            template=(
                "{context}\n\n"
                "Пользователь: {user_message}\n"
                "Ассистент: \n"
                "Структура JSON должна быть ровно следующей:\n"
                "content: строка, текст ответа;\n"
                "tags: список строк, метки сообщения;\n"
                "type: одно из ['авторизация', 'опллата', 'баги', 'вопросы по функционалу'];\n"
                "priority: одно из ['критический', 'высокий', 'средний', 'низкий'];\n"
                "Никаких дополнительных слов, объяснений, markdown или переносов строк.\n"
                "Должен быть только один JSON ответ;\n"
                "JSON должен обязательно содержать content, tags, type, priority;\n"
                "tags должен обязательно содержать список тегов;\n"
                "ОТВЕЧАЙ ТОЛЬКО СТРОГО В ФОРМАТЕ JSON."
            )
        )

        self.server_url = server_url or f"http://{os.environ.get("LLM_HOST")}:{os.environ.get("LLM_PORT")}"
        self.model_path = model_path or os.environ.get("LLM_PATH")
        if self.model_path is None:
            raise MissingModelPathException(f"{self.__class__.__name__}.__init__ didn't get mandatory LLM_PATH environment variable")
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", 256))
        self.timeout = int(os.environ.get("LLM_TIMEOUT", 5))
        self.retries = int(os.environ.get("LLM_RETRIES", 3))

        self._initialized = True

    async def send_message(
        self,
        user_message: str,
        conversation_context: list[dict[str, str]]
    ) -> tuple[str, str, list[str], str]:
        '''Method to send messages to the LLM through HTTP protocol.

        Sends history of messages to the LLM on a remote server with url [self.server_url] via httpx.
        Thus LLM has a consistent context of the conversation.

        Args:
            user_message (str): User's last message
            conversation_context (list[dict[str, str]]): History of messages

        Returns:
            tuple[str, str, list[str], str]: A tuple with message type, priority, tags, and LLM resonse text.

        Raises:
            FailedAllVllmRetries: Raised due to httpx network errors or is unable to parse the LLM's output into correct json format.
        '''

        context_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in conversation_context
        )
        prompt_text = self.prompt_template.format(
            context=context_text,
            user_message=user_message
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            counter = 0
            while counter < self.retries: 
                try:
                    resp = await client.post(
                        f"{self.server_url}/v1/completions",
                        headers=[
                            ("Content-Type", "application/json")
                        ],
                        json={
                            "model": self.model_path,
                            "max_tokens": self.max_tokens,
                            "prompt": prompt_text,
                            "temperature": 0.0,
                            "type": "json_schema",
                            "json_schema": {
                                "name": "json_formatted_llm_response",
                                "schema": MessageSchema.model_json_schema()
                            }
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    text = data["choices"][0]["text"].strip()
                    text = text[text.find("{"):text.find("}")+1]

                    parsed: MessageSchema = parser.parse(text)

                    return parsed.type, parsed.priority, parsed.tags, parsed.content
                except httpx.TimeoutException as e:
                    logger.error(f"{self.__class__.__name__}.send_message() got timeout exception", e)
                    continue
                except httpx.HTTPStatusError as e:
                    logger.error(f"{self.__class__.__name__}.send_message() got {e.response.status_code} status code from vLLM's response", e)
                    continue
                except OutputParserException as e:
                    logger.error(f"{self.__class__.__name__}.send_message() failed to parse LLM's output", e)
                    continue
                finally:
                    counter += 1
            raise VllmFailedAllRetriesException(f"{self.__class__.__name__}.send_message() failed to get response from LLM with all given retries")

