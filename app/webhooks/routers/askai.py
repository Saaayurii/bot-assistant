from dataclasses import asdict
from fastapi import APIRouter, HTTPException, status

import httpx

from utils.jsonl_logger import JsonlLogger
from utils.local_storage import LocalStorage
from utils.serialize_adapter import SerializeAdapter
from webhooks.schemas.askai import ChatRequest, MessageResponse
from business_logic.metamessage import Conversation, AssistantMessage, MessageRoleEnum, UserMessage
from utils.redis_storage import RedisClient
from llm.vllm_client import VLLMClient

router = APIRouter(prefix="/assistant_bot")

training_logger = JsonlLogger()

@router.post(
        "/chat", 
        response_model=MessageResponse,
        responses={
            200: {
                "description": "Assistant response",
                "content": {
                    "application/json": {
                        "example": {
                            "response_message": "Hello! How can I help you?",
                            "tags": ["greeting", "authorization", "cridentials"],
                            "priority": "average",
                            "msg_type": "faq"
                        }
                    }
                }
            },
            424: {
                "description": "No assistant response available.",
                "content": {"application/json": {"example": {"detail": "No assistant response available."}}}
            },
            500: {
                "description": "Internal server error.",
                "content": {"application/json": {"example": {"detail": "Internal Server Error"}}}
            },
            502: {
                "description": "Failed to notify human assistant.",
                "content": {"application/json": {"example": {"detail": "Failed to notify human assistant"}}}
            }
        }
    )
async def chat(data: ChatRequest):
    with LocalStorage() as storage:

        redis_client = RedisClient(serialize_adapter=SerializeAdapter())
        conversation = await redis_client.fetch_conversation(
            user_id=str(data.id),
            conv_id=str(data.conversation.id)
        )

        if not conversation:
            conversation = Conversation(
                    data.conversation.id, 
                    data.conversation.status, 
                    data.conversation.inbox_id, 
                )

        user_msg = UserMessage(
            content=data.content,
            id=data.sender.id,
            name=data.sender.name,
            email=data.sender.email,
            role=MessageRoleEnum.USER
        )

        conversation.add_message(user_msg)

        response = conversation.precompute_meta(data.content, storage)

        if response is None:
            messages = asdict(conversation).get("messages")
            if not isinstance(messages, list): raise ValueError("Conversation messages are missing or invalid")
            llm_response_tuple = await VLLMClient().send_message(data.content, messages)
            ai_msg = AssistantMessage.from_tuple(llm_response_tuple)
            conversation.add_message(ai_msg)
        else:
            conversation.add_message(response)

        await redis_client.save_conversation(
            user_id=str(data.id),
            conv_id=str(conversation.id),
            conversation=conversation
        )

        last_message = conversation.messages[-1]
        priority = getattr(last_message, "priority", None)


        if priority == "critical":
            try:
                async with httpx.AsyncClient() as client:
                    # !!! CHANGE API CALL !!!
                    await client.post("...", json={"conversation_id": conversation.id, "message": last_message.content})
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to notify human assistant: {e}"
                )

        if not isinstance(last_message, AssistantMessage):
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail="No assistant response available."
            )

        await training_logger.log_pair(
            user_message=user_msg.content,
            assistant_message=last_message.content,
            tags=last_message.tags,
            msg_type=last_message.msg_type,
            priority=last_message.priority
        )

        return MessageResponse(
            response_message=last_message.content,
            tags=last_message.tags,
            priority=last_message.priority,
            msg_type=last_message.msg_type
        )
